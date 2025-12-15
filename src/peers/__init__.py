"""
Peer Comparison Module for AI Investment Agent.

This module provides functionality for:
- Finding industry peers for a given ticker
- Comparing valuation, growth, profitability, and financial health metrics
- Ranking companies within peer groups
- Visualizing peer comparisons

Main Classes:
    - PeerFinder: Auto-detect and retrieve industry peers
    - PeerMetrics: Calculate and aggregate peer group metrics
    - PeerComparator: Compare companies across multiple dimensions
    - PeerVisualizer: Generate comparison reports and visualizations

Usage:
    from src.peers import PeerFinder, PeerComparator

    # Find peers
    finder = PeerFinder()
    peers = await finder.find_peers("AAPL")

    # Compare metrics
    comparator = PeerComparator()
    valuation = await comparator.compare_valuation("AAPL", peers)
"""

from src.peers.finder import PeerFinder
from src.peers.metrics import PeerMetrics
from src.peers.comparator import PeerComparator
from src.peers.visualizer import (
    generate_comparison_table,
    generate_ranking_data,
    format_comparison_report,
)

__all__ = [
    "PeerFinder",
    "PeerMetrics",
    "PeerComparator",
    "generate_comparison_table",
    "generate_ranking_data",
    "format_comparison_report",
]
