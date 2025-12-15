"""
Example usage of the Peer Comparison module.

This script demonstrates how to use the peer comparison functionality
to analyze a stock relative to its industry peers.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.peers import PeerFinder, PeerComparator
from src.peers.visualizer import (
    format_comparison_report,
    generate_ranking_data,
    create_quick_comparison_table,
)


async def basic_peer_analysis(ticker: str):
    """
    Perform basic peer analysis for a ticker.

    Args:
        ticker: Stock ticker symbol
    """
    print(f"\n{'='*80}")
    print(f"Peer Analysis for {ticker}")
    print(f"{'='*80}\n")

    # Step 1: Find peers
    print(f"Step 1: Finding industry peers for {ticker}...")
    finder = PeerFinder(max_peers=5)

    try:
        peers = await finder.find_peers(ticker)
        print(f"✓ Found {len(peers)} peers: {', '.join(peers)}")

        # Get sector info
        sector_info = await finder.get_sector_info(ticker)
        print(f"✓ Sector: {sector_info.sector}")
        print(f"✓ Industry: {sector_info.industry}")
        print()

    except Exception as e:
        print(f"✗ Error finding peers: {e}")
        return

    if not peers:
        print("No peers found. Exiting.")
        return

    # Step 2: Compare metrics
    print(f"Step 2: Comparing {ticker} against peer group...")
    comparator = PeerComparator()

    try:
        # Perform comprehensive comparison
        result = await comparator.compare_all(ticker, peers)

        # Display category scores
        print("\nCategory Scores:")
        print("-" * 40)
        category_scores = result.get_category_scores()
        for category, score in category_scores.items():
            print(f"  {category.replace('_', ' ').title():<25} {score:>6.1f}/100")

        if result.overall_score:
            print(f"\n  {'Overall Score':<25} {result.overall_score:>6.1f}/100")

        print()

    except Exception as e:
        print(f"✗ Error comparing metrics: {e}")
        return

    # Step 3: Show detailed valuation comparison
    if result.valuation:
        print("Step 3: Valuation Analysis")
        print("-" * 40)
        print(f"Score: {result.valuation.overall_score:.1f}/100")

        if result.valuation.strengths:
            print(f"\nStrengths ({len(result.valuation.strengths)}):")
            for metric in result.valuation.strengths[:3]:  # Top 3
                comp = result.valuation.metrics[metric]
                print(f"  • {metric}: {comp.ticker_value:.2f} "
                      f"(Rank {comp.ranking}/{comp.total_ranked})")

        if result.valuation.weaknesses:
            print(f"\nWeaknesses ({len(result.valuation.weaknesses)}):")
            for metric in result.valuation.weaknesses[:3]:  # Top 3
                comp = result.valuation.metrics[metric]
                print(f"  • {metric}: {comp.ticker_value:.2f} "
                      f"(Rank {comp.ranking}/{comp.total_ranked})")

        print()

    # Step 4: Generate report
    print("Step 4: Generating comprehensive report...")
    try:
        report = format_comparison_report(ticker, peers, result, include_details=False)
        print("\n" + "="*80)
        print(report)
        print("="*80)

        # Save to file
        report_file = Path(f"peer_comparison_{ticker}.md")
        report_file.write_text(report)
        print(f"\n✓ Full report saved to: {report_file.absolute()}")

    except Exception as e:
        print(f"✗ Error generating report: {e}")


async def compare_specific_peers(ticker: str, peer_list: list):
    """
    Compare against a specific list of peers.

    Args:
        ticker: Stock ticker symbol
        peer_list: List of peer ticker symbols
    """
    print(f"\n{'='*80}")
    print(f"Custom Peer Comparison: {ticker} vs {', '.join(peer_list)}")
    print(f"{'='*80}\n")

    comparator = PeerComparator()

    # Compare valuation
    print("Valuation Metrics:")
    try:
        valuation = await comparator.compare_valuation(ticker, peer_list)
        print(f"  Overall Score: {valuation.overall_score:.1f}/100")
        print(f"  Strengths: {len(valuation.strengths)}")
        print(f"  Weaknesses: {len(valuation.weaknesses)}")
    except Exception as e:
        print(f"  Error: {e}")

    # Compare growth
    print("\nGrowth Metrics:")
    try:
        growth = await comparator.compare_growth(ticker, peer_list)
        print(f"  Overall Score: {growth.overall_score:.1f}/100")
        print(f"  Strengths: {len(growth.strengths)}")
        print(f"  Weaknesses: {len(growth.weaknesses)}")
    except Exception as e:
        print(f"  Error: {e}")

    # Compare profitability
    print("\nProfitability Metrics:")
    try:
        profitability = await comparator.compare_profitability(ticker, peer_list)
        print(f"  Overall Score: {profitability.overall_score:.1f}/100")
        print(f"  Strengths: {len(profitability.strengths)}")
        print(f"  Weaknesses: {len(profitability.weaknesses)}")
    except Exception as e:
        print(f"  Error: {e}")

    # Compare financial health
    print("\nFinancial Health Metrics:")
    try:
        health = await comparator.compare_financial_health(ticker, peer_list)
        print(f"  Overall Score: {health.overall_score:.1f}/100")
        print(f"  Strengths: {len(health.strengths)}")
        print(f"  Weaknesses: {len(health.weaknesses)}")
    except Exception as e:
        print(f"  Error: {e}")

    print()


async def rank_by_metric(ticker: str, peers: list, metric: str):
    """
    Rank ticker within peer group by a specific metric.

    Args:
        ticker: Stock ticker symbol
        peers: List of peer tickers
        metric: Metric name to rank by
    """
    print(f"\n{'='*80}")
    print(f"Ranking by {metric}: {ticker}")
    print(f"{'='*80}\n")

    comparator = PeerComparator()

    try:
        rank, total, value = await comparator.rank_in_peer_group(ticker, peers, metric)

        print(f"Metric: {metric}")
        print(f"Value: {value}")
        print(f"Rank: {rank} out of {total}")
        print(f"Percentile: {((total - rank) / total * 100):.1f}%")

    except Exception as e:
        print(f"Error: {e}")

    print()


async def main():
    """Main entry point for examples."""
    # Example 1: Automatic peer detection and analysis
    await basic_peer_analysis("AAPL")

    # Example 2: Custom peer list
    # await compare_specific_peers("TSLA", ["GM", "F", "TM", "STLA"])

    # Example 3: Rank by specific metric
    # await rank_by_metric("AAPL", ["MSFT", "GOOGL", "META"], "pe_ratio")


if __name__ == "__main__":
    asyncio.run(main())
