"""
Integration tests for ticker-specific memory isolation - REAL ChromaDB.

These tests use REAL ChromaDB (not mocks) with the ACTUAL memory.py API.

IMPORTANT: These tests:
- Use the default ChromaDB directory (./chroma_db)
- Require GOOGLE_API_KEY environment variable
- Clean up all test data after running
- Are marked as @pytest.mark.integration for separate execution

Run with:
    export GOOGLE_API_KEY="your-key"
    pytest tests/test_memory_integration_live.py -v -m integration
"""

import pytest
import os

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


class TestRealTickerIsolation:
    """
    CRITICAL INTEGRATION TEST
    
    Verifies ticker-specific memory isolation with real ChromaDB.
    """
    
    @pytest.mark.asyncio
    async def test_different_tickers_use_different_collections(self):
        """
        THE MOST IMPORTANT TEST
        
        Verifies that analyzing different tickers creates separate ChromaDB collections
        and that data from one ticker does NOT appear in queries for another ticker.
        """
        # Skip if no real API key available
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("Requires GOOGLE_API_KEY environment variable")
        
        from src.memory import create_memory_instances, cleanup_all_memories
        
        try:
            # Step 1: Create memories for ticker AAPL
            aapl_memories = create_memory_instances("AAPL")
            
            # Verify we got 5 memory instances (bull, bear, trader, judge, risk_manager)
            assert len(aapl_memories) == 5
            assert "AAPL_bull_memory" in aapl_memories
            assert "AAPL_bear_memory" in aapl_memories
            assert "AAPL_trader_memory" in aapl_memories
            assert "AAPL_invest_judge_memory" in aapl_memories
            assert "AAPL_risk_manager_memory" in aapl_memories
        
            # Get bull memory
            aapl_bull = aapl_memories["AAPL_bull_memory"]
            
            # Skip if memory not available (no valid API key)
            if not aapl_bull.available:
                pytest.skip("Memory not available - API key may be invalid")
            
            # Step 2: Store AAPL-specific situations (ASYNC!)
            aapl_situations = [
                "AAPL is undervalued based on P/E ratio of 15",
                "Apple's services revenue growing 20% YoY",
                "Strong iPhone 15 sales in China market"
            ]
            await aapl_bull.add_situations(aapl_situations)
            
            # Step 3: Create memories for ticker MSFT
            msft_memories = create_memory_instances("MSFT")
            msft_bull = msft_memories["MSFT_bull_memory"]
            
            # Verify separate instances
            assert msft_bull is not aapl_bull
            assert msft_bull.name != aapl_bull.name
            assert "MSFT" in msft_bull.name
            assert "AAPL" in aapl_bull.name
            
            # Step 4: Store MSFT-specific situations (ASYNC!)
            msft_situations = [
                "MSFT has high debt levels at 60B USD",
                "Azure cloud revenue declining 5% QoQ",
                "Microsoft facing regulatory scrutiny in EU"
            ]
            await msft_bull.add_situations(msft_situations)
            
            # Step 5: THE CRITICAL TEST - Query MSFT memories (ASYNC with ticker!)
            msft_results = await msft_bull.get_relevant_memory(
                ticker="MSFT",
                situation_summary="What is the company's valuation?",
                n_results=10
            )
            
            # Verify results exist
            assert msft_results is not None, "MSFT query should return results"
            assert len(msft_results) > 0, "Should have MSFT results"
            
            # CRITICAL ASSERTIONS - No AAPL contamination
            assert "AAPL" not in msft_results, f"AAPL data contaminated MSFT memory! Results: {msft_results}"
            assert "Apple" not in msft_results, f"Apple data contaminated MSFT memory! Results: {msft_results}"
            assert "iPhone" not in msft_results, f"iPhone data contaminated MSFT memory! Results: {msft_results}"
            
            # Verify MSFT data IS present
            assert "MSFT" in msft_results or "debt" in msft_results or "Azure" in msft_results, \
                f"MSFT query should return MSFT-related content. Got: {msft_results}"
            
            # Step 6: Verify AAPL query doesn't have MSFT data (ASYNC with ticker!)
            aapl_results = await aapl_bull.get_relevant_memory(
                ticker="AAPL",
                situation_summary="What is the debt situation?",
                n_results=10
            )
            
            assert aapl_results is not None
            
            # AAPL memories should NOT contain MSFT data
            assert "MSFT" not in aapl_results, f"MSFT data contaminated AAPL memory! Results: {aapl_results}"
            assert "Azure" not in aapl_results, f"Azure data contaminated AAPL memory! Results: {aapl_results}"
            assert "Microsoft" not in aapl_results, f"Microsoft data contaminated AAPL memory! Results: {aapl_results}"
            
        finally:
            # Cleanup - remove all test collections (SYNC!)
            cleanup_all_memories(days=0)
    
    @pytest.mark.asyncio
    async def test_memory_persistence_across_instances(self):
        """
        Verify that memory persists when you create new instances.
        
        Simulates: Run analysis for AAPL, create new instances, memories still there.
        """
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("Requires GOOGLE_API_KEY environment variable")
        
        from src.memory import create_memory_instances, cleanup_all_memories
        
        try:
            # Session 1: Create and store
            session1_memories = create_memory_instances("AAPL")
            session1_bull = session1_memories["AAPL_bull_memory"]
            
            # Skip if not available
            if not session1_bull.available:
                pytest.skip("Memory not available - API key may be invalid")
            
            test_situations = [
                "AAPL has strong fundamentals",
                "Apple's P/E ratio is attractive at 15"
            ]
            await session1_bull.add_situations(test_situations)
            
            # Verify data was stored (ASYNC with ticker!)
            query_results = await session1_bull.get_relevant_memory(
                ticker="AAPL",
                situation_summary="fundamentals",
                n_results=5
            )
            assert query_results is not None
            assert len(query_results) > 0
            
            # Create NEW instances (simulating restart)
            session2_memories = create_memory_instances("AAPL")
            session2_bull = session2_memories["AAPL_bull_memory"]
            
            # Different instance
            assert session2_bull is not session1_bull
            
            # But should read from same ChromaDB collection (ASYNC with ticker!)
            persisted_results = await session2_bull.get_relevant_memory(
                ticker="AAPL",
                situation_summary="fundamentals",
                n_results=5
            )
            
            assert persisted_results is not None, "Memory should persist across instances"
            assert len(persisted_results) > 0, "Should retrieve stored situations"
            
            assert "fundamentals" in persisted_results.lower() or "P/E" in persisted_results or "AAPL" in persisted_results, \
                f"Should retrieve relevant stored content. Got: {persisted_results}"
        
        finally:
            # SYNC cleanup
            cleanup_all_memories(days=0)
    
    @pytest.mark.asyncio
    async def test_cleanup_removes_all_ticker_collections(self):
        """
        Verify that cleanup actually removes collections.
        """
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("Requires GOOGLE_API_KEY environment variable")
        
        from src.memory import create_memory_instances, cleanup_all_memories, get_all_memory_stats
        
        try:
            # Create memories for multiple tickers
            aapl_memories = create_memory_instances("AAPL")
            msft_memories = create_memory_instances("MSFT")
            
            # Skip if not available
            if not aapl_memories["AAPL_bull_memory"].available:
                pytest.skip("Memory not available - API key may be invalid")
            
            # Add data to both (ASYNC!)
            await aapl_memories["AAPL_bull_memory"].add_situations(["AAPL situation 1"])
            await msft_memories["MSFT_bull_memory"].add_situations(["MSFT situation 1"])
            
            # Get stats before cleanup
            stats_before = get_all_memory_stats()
            assert len(stats_before) >= 10, "Should have at least 10 collections (5 per ticker)"
            
            # Cleanup all (SYNC!)
            cleanup_stats = cleanup_all_memories(days=0)
            
            # Verify cleanup happened
            assert len(cleanup_stats) >= 10, "Should have cleaned up all collections"
            
            # Get stats after cleanup
            stats_after = get_all_memory_stats()
            assert len(stats_after) == 0, "All collections should be removed after cleanup"
        
        finally:
            # Extra cleanup to be sure (SYNC!)
            cleanup_all_memories(days=0)


class TestRealMemoryOperations:
    """Test actual memory operations with real ChromaDB."""
    
    @pytest.mark.asyncio
    async def test_add_and_query_with_real_embeddings(self):
        """
        Basic sanity test: Can we add situations and query them back?
        """
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("Requires GOOGLE_API_KEY environment variable")
        
        from src.memory import create_memory_instances, cleanup_all_memories
        
        try:
            memories = create_memory_instances("TEST")
            memory = memories["TEST_bull_memory"]
            
            # Skip if not available
            if not memory.available:
                pytest.skip("Memory not available - API key may be invalid")
            
            # Add some situations (ASYNC!)
            situations = [
                "The company has strong revenue growth of 25% YoY",
                "Operating margins improved from 15% to 20%",
                "Debt to equity ratio is concerning at 2.5",
            ]
            
            await memory.add_situations(situations)
            
            # Query for revenue-related content (ASYNC with ticker!)
            revenue_results = await memory.get_relevant_memory(
                ticker="TEST",
                situation_summary="revenue growth",
                n_results=3
            )
            assert revenue_results is not None
            assert len(revenue_results) > 0
            
            # Should retrieve revenue-related situation
            assert "revenue" in revenue_results.lower() or "growth" in revenue_results.lower(), \
                f"Should find revenue content. Got: {revenue_results}"
        
        finally:
            # SYNC cleanup
            cleanup_all_memories(days=0)
    
    @pytest.mark.asyncio
    async def test_cleanup_respects_time_filter(self):
        """
        Test that cleanup with days_to_keep parameter works.
        """
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("Requires GOOGLE_API_KEY environment variable")

        from src.memory import create_memory_instances, cleanup_all_memories
        
        try:
            memories = create_memory_instances("TEST")
            memory = memories["TEST_bull_memory"]
            
            # Skip if not available
            if not memory.available:
                pytest.skip("Memory not available - API key may be invalid")
            
            # Add situations (ASYNC!)
            await memory.add_situations(["Situation 1", "Situation 2"])
            
            # Get initial count
            stats = memory.get_stats()
            initial_count = stats.get("document_count", 0)
            assert initial_count == 2
            
            # Cleanup with days_to_keep=30 should NOT delete recent memories (SYNC!)
            deleted = memory.clear_old_memories(days_to_keep=30)
            assert deleted == 0, "Recent memories should not be deleted"
            
            # Verify still there
            stats_after = memory.get_stats()
            assert stats_after.get("document_count", 0) == 2
            
            # Cleanup with days_to_keep=0 should delete everything (SYNC!)
            deleted = memory.clear_old_memories(days_to_keep=0)
            assert deleted == 2, "Should delete all memories when days_to_keep=0"
            
            # Verify deleted
            stats_final = memory.get_stats()
            assert stats_final.get("document_count", 0) == 0
        
        finally:
            # SYNC cleanup
            cleanup_all_memories(days=0)


# Configuration for pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (slow, requires real ChromaDB)"
    )