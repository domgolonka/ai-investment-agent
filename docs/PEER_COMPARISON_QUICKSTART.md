# Peer Comparison Module - Quick Start Guide

Get started with peer comparison analysis in 5 minutes.

## Installation

The peer comparison module is already integrated into the AI Investment Agent. No additional installation required - all dependencies are in `pyproject.toml`.

## Basic Usage

### 1. Find Peers Automatically

```python
import asyncio
from src.peers import PeerFinder

async def find_peers_example():
    finder = PeerFinder()
    peers = await finder.find_peers("AAPL")
    print(f"Apple's peers: {peers}")
    # Output: ['MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', ...]

asyncio.run(find_peers_example())
```

### 2. Compare Against Peers

```python
from src.peers import PeerFinder, PeerComparator

async def compare_example():
    # Find peers
    finder = PeerFinder(max_peers=5)
    peers = await finder.find_peers("AAPL")

    # Compare
    comparator = PeerComparator()
    result = await comparator.compare_all("AAPL", peers)

    # Print scores
    print(f"Overall Score: {result.overall_score:.1f}/100")
    print(f"Valuation: {result.valuation.overall_score:.1f}/100")
    print(f"Growth: {result.growth.overall_score:.1f}/100")
    print(f"Profitability: {result.profitability.overall_score:.1f}/100")
    print(f"Financial Health: {result.financial_health.overall_score:.1f}/100")

asyncio.run(compare_example())
```

### 3. Generate a Report

```python
from src.peers import PeerFinder, PeerComparator
from src.peers.visualizer import format_comparison_report

async def report_example():
    # Find and compare
    finder = PeerFinder()
    peers = await finder.find_peers("AAPL")

    comparator = PeerComparator()
    result = await comparator.compare_all("AAPL", peers)

    # Generate markdown report
    report = format_comparison_report("AAPL", peers, result)

    # Save to file
    with open("apple_peer_analysis.md", "w") as f:
        f.write(report)

    print("Report saved to apple_peer_analysis.md")

asyncio.run(report_example())
```

## Common Use Cases

### Custom Peer Group

Compare against a specific set of competitors:

```python
async def custom_peers():
    comparator = PeerComparator()

    # Define custom peer group
    ticker = "TSLA"
    peers = ["GM", "F", "TM", "STLA"]

    # Compare
    result = await comparator.compare_all(ticker, peers)
    print(f"{ticker} Overall Score: {result.overall_score:.1f}/100")

asyncio.run(custom_peers())
```

### Rank by Specific Metric

Find out where a stock ranks on a particular metric:

```python
async def rank_by_metric():
    finder = PeerFinder()
    comparator = PeerComparator()

    # Find peers
    peers = await finder.find_peers("AAPL")

    # Rank by P/E ratio
    rank, total, value = await comparator.rank_in_peer_group(
        "AAPL", peers, "pe_ratio"
    )

    print(f"Apple P/E: {value:.2f}")
    print(f"Rank: {rank} out of {total}")

asyncio.run(rank_by_metric())
```

### Compare Specific Categories

Focus on just one dimension of comparison:

```python
async def compare_valuation_only():
    finder = PeerFinder()
    comparator = PeerComparator()

    peers = await finder.find_peers("AAPL")

    # Just valuation
    valuation = await comparator.compare_valuation("AAPL", peers)

    print(f"Valuation Score: {valuation.overall_score:.1f}/100")
    print(f"Strengths: {valuation.strengths}")
    print(f"Weaknesses: {valuation.weaknesses}")

asyncio.run(compare_valuation_only())
```

## Running the Example

A complete example is provided in `examples/peer_comparison_example.py`:

```bash
python examples/peer_comparison_example.py
```

This will:
1. Find peers for Apple (AAPL)
2. Compare across all categories
3. Generate a detailed markdown report
4. Save the report to `peer_comparison_AAPL.md`

## Understanding the Scores

- **Scores are 0-100**: Higher is better (represents percentile rank)
- **75+ = Strong**: Top quartile among peers
- **50-75 = Above Average**: Better than median
- **25-50 = Below Average**: Below median
- **<25 = Weak**: Bottom quartile among peers

## Key Metrics Explained

### Valuation (Lower is Often Better)
- **P/E Ratio**: Price relative to earnings
- **P/B Ratio**: Price relative to book value
- **EV/EBITDA**: Enterprise value to EBITDA multiple

### Growth (Higher is Better)
- **Revenue Growth**: Year-over-year revenue increase
- **Earnings Growth**: Year-over-year earnings increase

### Profitability (Higher is Better)
- **Profit Margin**: Net income / revenue
- **ROE**: Return on equity
- **ROA**: Return on assets

### Financial Health
- **Debt/Equity**: Lower is often better
- **Current Ratio**: Higher indicates better short-term health
- **Free Cash Flow**: Higher is better

## Tips & Best Practices

1. **Cache Considerations**: Sector info is cached for 24 hours by default. Use `finder.clear_cache()` to force refresh.

2. **Market Cap Filtering**: By default, peers must be within 0.1x to 10x the market cap. Adjust if needed:
   ```python
   finder = PeerFinder(
       min_market_cap_ratio=0.5,  # At least 50% of focus ticker
       max_market_cap_ratio=2.0,  # At most 200% of focus ticker
   )
   ```

3. **International Tickers**: Works with international tickers using exchange suffixes:
   ```python
   peers = await finder.find_peers("NESN.SW")  # Nestle (Swiss)
   ```

4. **Same Country Filter**: Limit to domestic peers:
   ```python
   peers = await finder.find_peers("AAPL", same_country=True)
   ```

5. **Error Handling**: The module gracefully handles missing data - if a metric isn't available, it's excluded from comparison.

## Next Steps

- Read the full documentation: `src/peers/README.md`
- Check the test suite: `tests/test_peers.py`
- Review the implementation for integration patterns

## Support

For issues or questions:
1. Check the comprehensive README at `src/peers/README.md`
2. Review the example script at `examples/peer_comparison_example.py`
3. Examine the test suite at `tests/test_peers.py` for usage patterns

---

**Note**: This module uses yfinance for data. Ensure you have a stable internet connection and be mindful of API rate limits when analyzing large peer groups.
