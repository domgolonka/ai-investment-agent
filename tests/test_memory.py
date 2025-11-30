"""
Tests for Core FinancialSituationMemory Class

This file tests the core FinancialSituationMemory class methods and behavior.

NOT covered here (see other test files):
- Ticker-specific isolation → test_memory_isolation.py
- Ticker sanitization → test_memory_isolation.py  
- create_memory_instances() → test_memory_isolation.py
- cleanup_all_memories() → test_memory_isolation.py
- get_all_memory_stats() → test_memory_isolation.py
- Graph integration → test_memory_integration.py

Focus:
- Memory initialization and availability detection
- Situation storage and retrieval
- Memory cleanup (per-instance)
- Statistics (per-instance)
"""

import pytest
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from src.memory import FinancialSituationMemory


class TestFinancialSituationMemoryInitialization:
    """Test memory initialization under various conditions."""
    
    def test_init_without_api_key(self):
        """Memory should gracefully handle missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            memory = FinancialSituationMemory("test_memory")
            
            assert memory.name == "test_memory"
            assert memory.available == False
            assert memory.embeddings is None
            assert memory.situation_collection is None
    
    def test_init_with_embedding_failure(self):
        """Memory should handle embedding initialization failures."""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('src.memory.GoogleGenerativeAIEmbeddings', side_effect=Exception("API error")):
                memory = FinancialSituationMemory("test_memory")
                
                assert memory.available == False
                assert memory.embeddings is None
    
    def test_init_with_chromadb_failure(self):
        """Memory should handle ChromaDB connection failures."""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('src.memory.GoogleGenerativeAIEmbeddings') as mock_embeddings_class:
                mock_embeddings = MagicMock()
                mock_embeddings.embed_query.return_value = [0.1] * 768
                mock_embeddings_class.return_value = mock_embeddings
                
                with patch('chromadb.PersistentClient', side_effect=Exception("Connection failed")):
                    memory = FinancialSituationMemory("test_memory")
                    
                    assert memory.available == False
                    assert memory.situation_collection is None
    
    def test_successful_init(self):
        """Memory should initialize successfully with valid configuration."""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('src.memory.GoogleGenerativeAIEmbeddings') as mock_embeddings_class:
                mock_embeddings = MagicMock()
                mock_embeddings.embed_query.return_value = [0.1] * 768
                mock_embeddings_class.return_value = mock_embeddings
                
                with patch('chromadb.PersistentClient') as mock_client_class:
                    mock_client = MagicMock()
                    mock_collection = MagicMock()
                    mock_collection.count.return_value = 0
                    mock_client.get_or_create_collection.return_value = mock_collection
                    mock_client_class.return_value = mock_client
                    
                    memory = FinancialSituationMemory("test_memory")
                    
                    assert memory.name == "test_memory"
                    assert memory.available == True
                    assert memory.embeddings is not None
                    assert memory.situation_collection is not None


class TestSituationStorage:
    """Test adding financial situations to memory."""
    
    @pytest.mark.asyncio
    async def test_add_situations_unavailable(self):
        """add_situations should return False when memory unavailable."""
        memory = FinancialSituationMemory("test_memory")
        
        result = await memory.add_situations(["Test situation"])
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_add_situations_empty_list(self):
        """add_situations should return False for empty list."""
        memory = FinancialSituationMemory("test_memory")
        memory.available = True
        
        result = await memory.add_situations([])
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_add_situations_success(self):
        """add_situations should successfully store situations."""
        memory = FinancialSituationMemory("test_memory")
        memory.available = True
        memory._get_embedding = AsyncMock(return_value=[0.1] * 768)
        memory.situation_collection = MagicMock()
        
        situations = ["AAPL strong buy signal", "Market momentum positive"]
        result = await memory.add_situations(situations)
        
        assert result == True
        
        # Verify collection.add was called
        assert memory.situation_collection.add.called
        call_kwargs = memory.situation_collection.add.call_args[1]
        
        # Check that all required fields were provided
        assert 'embeddings' in call_kwargs
        assert 'documents' in call_kwargs
        assert 'ids' in call_kwargs
        assert 'metadatas' in call_kwargs
        
        # Check correct number of items
        assert len(call_kwargs['documents']) == 2
        assert len(call_kwargs['embeddings']) == 2


class TestSituationQuerying:
    """Test querying similar situations from memory."""
    
    @pytest.mark.asyncio
    async def test_query_unavailable(self):
        """query_similar_situations should return empty list when unavailable."""
        memory = FinancialSituationMemory("test_memory")
        
        results = await memory.query_similar_situations("test query")
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_query_success(self):
        """query_similar_situations should return formatted results."""
        memory = FinancialSituationMemory("test_memory")
        memory.available = True
        memory._get_embedding = AsyncMock(return_value=[0.1] * 768)
        memory.situation_collection = MagicMock()
        
        # Mock ChromaDB query response
        memory.situation_collection.query.return_value = {
            'documents': [["AAPL strong fundamentals", "MSFT growing revenue"]],
            'metadatas': [[{"ticker": "AAPL"}, {"ticker": "MSFT"}]],
            'distances': [[0.1, 0.2]]
        }
        
        results = await memory.query_similar_situations("tech stocks", n_results=2)
        
        assert len(results) == 2
        assert results[0]['document'] == "AAPL strong fundamentals"
        assert results[0]['metadata']['ticker'] == "AAPL"
        assert results[0]['distance'] == 0.1
        assert results[1]['document'] == "MSFT growing revenue"


class TestGetRelevantMemory:
    """Test high-level memory retrieval for agent context."""
    
    @pytest.mark.asyncio
    async def test_get_relevant_memory_no_results(self):
        """get_relevant_memory should handle no results gracefully."""
        memory = FinancialSituationMemory("test_memory")
        memory.available = True
        memory.query_similar_situations = AsyncMock(return_value=[])
        
        result = await memory.get_relevant_memory("AAPL", "analysis")
        
        assert "No relevant past memories found" in result
    
    @pytest.mark.asyncio
    async def test_get_relevant_memory_success(self):
        """get_relevant_memory should format results for display."""
        memory = FinancialSituationMemory("test_memory")
        memory.available = True
        
        mock_results = [
            {
                'document': "AAPL shows strong fundamentals with growing revenue",
                'metadata': {'ticker': 'AAPL', 'timestamp': '2024-01-01T00:00:00'},
                'distance': 0.1
            }
        ]
        memory.query_similar_situations = AsyncMock(return_value=mock_results)
        
        result = await memory.get_relevant_memory("AAPL", "fundamental analysis")
        
        assert "Relevant past memories for AAPL" in result
        assert "AAPL shows strong fundamentals" in result


class TestMemoryCleanup:
    """Test memory cleanup functionality."""
    
    def test_cleanup_unavailable(self):
        """clear_old_memories should return 0 when unavailable."""
        memory = FinancialSituationMemory("test_memory")
        
        deleted = memory.clear_old_memories(days_to_keep=30)
        
        assert deleted == 0
    
    def test_cleanup_no_old_memories(self):
        """clear_old_memories should return 0 when no old memories."""
        memory = FinancialSituationMemory("test_memory")
        memory.available = True
        memory.situation_collection = MagicMock()
        
        # Mock response with no old documents
        memory.situation_collection.get.return_value = {
            'ids': [],
            'metadatas': []
        }
        
        deleted = memory.clear_old_memories(days_to_keep=30)
        
        assert deleted == 0
    
    def test_cleanup_with_old_memories(self):
        """clear_old_memories should delete old documents."""
        memory = FinancialSituationMemory("test_memory")
        memory.available = True
        memory.situation_collection = MagicMock()
        
        # Create old and new timestamps
        old_timestamp = (datetime.now() - timedelta(days=100)).isoformat()
        new_timestamp = datetime.now().isoformat()
        
        memory.situation_collection.get.return_value = {
            'ids': ['old_1', 'new_1'],
            'metadatas': [
                {'timestamp': old_timestamp},
                {'timestamp': new_timestamp}
            ]
        }
        
        deleted = memory.clear_old_memories(days_to_keep=30)
        
        # Should delete only the old document
        assert deleted == 1
        memory.situation_collection.delete.assert_called_once_with(ids=['old_1'])


class TestMemoryStats:
    """Test memory statistics retrieval."""
    
    def test_stats_unavailable(self):
        """get_stats should return unavailable status."""
        memory = FinancialSituationMemory("test_memory")
        
        stats = memory.get_stats()
        
        assert stats['available'] == False
        assert stats['name'] == "test_memory"
        assert stats['count'] == 0
    
    def test_stats_success(self):
        """get_stats should return collection information."""
        memory = FinancialSituationMemory("test_memory")
        memory.available = True
        memory.situation_collection = MagicMock()
        memory.situation_collection.count.return_value = 42
        
        stats = memory.get_stats()
        
        assert stats['available'] == True
        assert stats['name'] == "test_memory"
        assert stats['count'] == 42


class TestExportedInstances:
    """Test that legacy global memory instances exist for backward compatibility."""
    
    def test_exported_instances_exist(self):
        """Legacy global memory instances should be importable."""
        from src.memory import (
            bull_memory,
            bear_memory,
            trader_memory,
            invest_judge_memory,
            risk_manager_memory
        )
        
        # All should be FinancialSituationMemory instances
        assert isinstance(bull_memory, FinancialSituationMemory)
        assert isinstance(bear_memory, FinancialSituationMemory)
        assert isinstance(trader_memory, FinancialSituationMemory)
        assert isinstance(invest_judge_memory, FinancialSituationMemory)
        assert isinstance(risk_manager_memory, FinancialSituationMemory)
    
    def test_exported_instances_are_unique(self):
        """Each legacy instance should be distinct."""
        from src.memory import bull_memory, bear_memory, trader_memory
        
        assert bull_memory is not bear_memory
        assert bear_memory is not trader_memory
        assert bull_memory is not trader_memory


@pytest.mark.skip(reason="Memory not available")
@pytest.mark.asyncio
async def test_full_memory_workflow():
    """Integration test of full memory workflow (only runs if memory available)."""
    memory = FinancialSituationMemory("workflow_test")
    
    if not memory.available:
        pytest.skip("Memory not available for integration test")
    
    # Add situations
    await memory.add_situations([
        "AAPL shows strong momentum",
        "Tech sector bullish outlook"
    ])
    
    # Query back
    results = await memory.query_similar_situations("Apple stock analysis", n_results=1)
    assert len(results) > 0
    
    # Get formatted memory
    formatted = await memory.get_relevant_memory("AAPL", "momentum")
    assert "AAPL" in formatted
    
    # Check stats
    stats = memory.get_stats()
    assert stats['count'] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])