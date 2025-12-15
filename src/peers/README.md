# Peer Comparison Module

Comprehensive peer comparison functionality for the AI Investment Agent, enabling automatic peer detection, multi-dimensional financial analysis, and ranking within industry peer groups.

## Features

- **Automatic Peer Detection**: Uses yfinance sector/industry classification to identify peers
- **Multi-dimensional Comparison**: Valuation, growth, profitability, and financial health
- **Percentile Ranking**: Understand where a company stands relative to peers
- **Caching**: Minimizes API calls with intelligent caching
- **International Support**: Works with tickers from global exchanges
- **Visualization**: Generate reports, tables, and ranking data for charts

## Architecture

### Module Structure

```
src/peers/
├── __init__.py          # Module exports
├── finder.py            # PeerFinder - Auto-detect peers
├── metrics.py           # PeerMetrics - Fetch and aggregate metrics
├── comparator.py        # PeerComparator - Compare across dimensions
├── visualizer.py        # Visualization and reporting utilities
└── README.md            # This file
```

### Core Classes

#### 1. PeerFinder
Automatically detects and retrieves industry peers for a given ticker.

**Key Features:**
- Auto-detect peers by sector and industry
- Market cap filtering for comparable companies
- Support for international tickers
- Intelligent caching (24-hour TTL by default)
- Configurable peer group size

**Methods:**
- `find_peers(ticker, max_peers=10)` - Find peers for a ticker
- `find_peers_by_sector(sector, industry=None)` - Get all tickers in a sector
- `get_sector_info(ticker)` - Get sector/industry classification
- `clear_cache()` - Clear cached data

#### 2. PeerMetrics
Fetches comprehensive financial metrics for peer groups with concurrent processing.

**Key Features:**
- Concurrent metric fetching (up to 10 tickers in parallel)
- 40+ financial metrics per ticker
- Statistical aggregation (median, mean, percentiles)
- Outlier detection
- Data coverage reporting

**Methods:**
- `get_peer_metrics(tickers)` - Fetch metrics for multiple tickers
- `calculate_metric_stats(metrics, metric_name)` - Get peer group statistics
- `calculate_peer_median(metrics)` - Median for all metrics
- `calculate_peer_average(metrics)` - Average for all metrics
- `calculate_percentile(ticker_value, peer_values)` - Percentile rank
- `get_metric_ranking(metrics, metric_name)` - Ranked list

#### 3. PeerComparator
Compares companies across valuation, growth, profitability, and financial health.

**Key Features:**
- Multi-category comparison
- Automatic strength/weakness identification
- Percentile-based scoring (0-100)
- Weighted overall score
- Ranking within peer group

**Methods:**
- `compare_valuation(ticker, peers)` - P/E, P/B, EV/EBITDA comparison
- `compare_growth(ticker, peers)` - Revenue, earnings growth
- `compare_profitability(ticker, peers)` - Margins, ROE, ROA
- `compare_financial_health(ticker, peers)` - D/E, current ratio
- `compare_all(ticker, peers)` - Comprehensive analysis
- `rank_in_peer_group(ticker, peers, metric)` - Rank by specific metric

#### 4. Visualizer
Generates comparison tables, ranking data, and markdown reports.

**Key Functions:**
- `generate_comparison_table(ticker, peers, metrics)` - Tabular data
- `generate_ranking_data(ticker, peers, result)` - Chart-ready data
- `format_comparison_report(ticker, peers, result)` - Markdown report
- `create_quick_comparison_table(ticker, peers, metrics)` - Text table

## Usage Examples

### Basic Usage: Automatic Peer Detection

```python
import asyncio
from src.peers import PeerFinder, PeerComparator

async def analyze_stock(ticker: str):
    # Step 1: Find peers
    finder = PeerFinder(max_peers=5)
    peers = await finder.find_peers(ticker)
    print(f"Peers: {peers}")

    # Step 2: Compare
    comparator = PeerComparator()
    result = await comparator.compare_all(ticker, peers)

    # Step 3: Display results
    print(f"Overall Score: {result.overall_score:.1f}/100")
    print(f"Valuation: {result.valuation.overall_score:.1f}/100")
    print(f"Growth: {result.growth.overall_score:.1f}/100")
    print(f"Profitability: {result.profitability.overall_score:.1f}/100")
    print(f"Financial Health: {result.financial_health.overall_score:.1f}/100")

asyncio.run(analyze_stock("AAPL"))
```

### Advanced Usage: Custom Peer Group

```python
from src.peers import PeerComparator
from src.peers.visualizer import format_comparison_report

async def custom_comparison():
    # Define custom peer group
    ticker = "TSLA"
    peers = ["GM", "F", "TM", "STLA"]

    comparator = PeerComparator()

    # Valuation analysis
    valuation = await comparator.compare_valuation(ticker, peers)
    print(f"Valuation Score: {valuation.overall_score:.1f}/100")
    print(f"Strengths: {valuation.strengths}")
    print(f"Weaknesses: {valuation.weaknesses}")

    # Get complete comparison
    result = await comparator.compare_all(ticker, peers)

    # Generate markdown report
    report = format_comparison_report(ticker, peers, result)
    with open("tesla_peer_report.md", "w") as f:
        f.write(report)

asyncio.run(custom_comparison())
```

### Ranking by Specific Metric

```python
from src.peers import PeerFinder, PeerComparator

async def rank_by_pe_ratio(ticker: str):
    # Find peers
    finder = PeerFinder()
    peers = await finder.find_peers(ticker)

    # Rank by P/E ratio
    comparator = PeerComparator()
    rank, total, value = await comparator.rank_in_peer_group(
        ticker, peers, "pe_ratio"
    )

    print(f"{ticker} P/E Ratio: {value:.2f}")
    print(f"Rank: {rank} out of {total}")
    print(f"Percentile: {((total - rank) / total * 100):.1f}%")

asyncio.run(rank_by_pe_ratio("AAPL"))
```

### Generate Comparison Table

```python
from src.peers import PeerFinder, PeerMetrics
from src.peers.visualizer import create_quick_comparison_table

async def show_comparison_table(ticker: str):
    # Find peers and fetch metrics
    finder = PeerFinder(max_peers=5)
    peers = await finder.find_peers(ticker)

    metrics_helper = PeerMetrics()
    all_metrics = await metrics_helper.get_peer_metrics([ticker] + peers)

    # Generate table
    table = create_quick_comparison_table(
        ticker,
        peers,
        all_metrics,
        key_metrics=["pe_ratio", "revenue_growth", "profit_margin", "roe"]
    )

    print(table)

asyncio.run(show_comparison_table("AAPL"))
```

## Metrics Covered

### Valuation Metrics
- `pe_ratio` - Trailing P/E Ratio
- `forward_pe` - Forward P/E Ratio
- `pb_ratio` - Price-to-Book Ratio
- `ps_ratio` - Price-to-Sales Ratio
- `ev_ebitda` - Enterprise Value / EBITDA
- `peg_ratio` - PEG Ratio

### Growth Metrics
- `revenue_growth` - Revenue Growth (trailing)
- `earnings_growth` - Earnings Growth (trailing)
- `revenue_growth_yoy` - Revenue Growth YoY
- `earnings_growth_yoy` - Earnings Growth YoY

### Profitability Metrics
- `profit_margin` - Net Profit Margin
- `operating_margin` - Operating Margin
- `gross_margin` - Gross Margin
- `roe` - Return on Equity
- `roa` - Return on Assets
- `roic` - Return on Invested Capital

### Financial Health Metrics
- `debt_to_equity` - Debt-to-Equity Ratio
- `current_ratio` - Current Ratio
- `quick_ratio` - Quick Ratio
- `free_cash_flow` - Free Cash Flow
- `total_cash` - Total Cash
- `total_debt` - Total Debt

### Other Metrics
- `market_cap` - Market Capitalization
- `enterprise_value` - Enterprise Value
- `beta` - Beta (volatility)
- `dividend_yield` - Dividend Yield

## Configuration

### PeerFinder Configuration

```python
finder = PeerFinder(
    cache_ttl_hours=24,          # Cache TTL for sector info
    max_peers=10,                # Default max peers to return
    min_market_cap_ratio=0.1,    # Min market cap as ratio of focus
    max_market_cap_ratio=10.0,   # Max market cap as ratio of focus
)

# Find peers with custom parameters
peers = await finder.find_peers(
    ticker="AAPL",
    max_peers=5,
    same_country=True,           # Only US-based peers
    min_market_cap=100e9,        # Minimum $100B market cap
)
```

### PeerMetrics Configuration

```python
metrics_helper = PeerMetrics(
    fetch_timeout=15,            # Timeout per ticker (seconds)
    max_concurrent=10,           # Max concurrent API requests
)
```

### PeerComparator Configuration

```python
# Use custom weights for overall score
result = await comparator.compare_all(
    ticker="AAPL",
    peers=peers,
    weights={
        "valuation": 0.30,
        "growth": 0.30,
        "profitability": 0.25,
        "financial_health": 0.15,
    }
)
```

## Data Sources

- **Primary**: yfinance for all financial metrics and sector/industry classification
- **Fallback**: The module is designed to integrate with the project's multi-source data fetcher if needed

## Caching Strategy

1. **Sector Info Cache**:
   - TTL: 24 hours (configurable)
   - Reduces repeated API calls for sector/industry lookups
   - Automatically expires stale data

2. **Industry Ticker Lists**:
   - Cached after first lookup
   - Grows organically as more tickers are analyzed
   - Can be cleared with `clear_cache()`

## Error Handling

The module uses the project's exception hierarchy from `src/exceptions.py`:

- `DataFetchError` - Failed to fetch data from yfinance
- `TickerNotFoundError` - Ticker symbol not found
- `DataValidationError` - Invalid or missing data

All async methods handle exceptions gracefully and log warnings for partial failures.

## Performance Characteristics

- **Peer Detection**: ~2-5 seconds for 10 peers (with caching)
- **Metric Fetching**: ~5-10 seconds for 10 tickers (concurrent)
- **Full Comparison**: ~10-15 seconds for complete analysis

Concurrent processing ensures scalability for larger peer groups.

## Testing

Run the example script to test the module:

```bash
python examples/peer_comparison_example.py
```

## Integration with AI Agent

The peer comparison module integrates seamlessly with the AI Investment Agent:

```python
# In your agent workflow
from src.peers import PeerFinder, PeerComparator

class PeerAnalysisAgent:
    async def analyze(self, ticker: str):
        # Find peers
        finder = PeerFinder()
        peers = await finder.find_peers(ticker)

        # Compare
        comparator = PeerComparator()
        result = await comparator.compare_all(ticker, peers)

        # Generate insights
        insights = self._generate_insights(result)

        return {
            "peers": peers,
            "comparison": result,
            "insights": insights,
        }
```

## Future Enhancements

Potential improvements for future versions:

1. **Expanded Peer Database**: Integrate with comprehensive ticker databases
2. **Sector ETF Benchmarking**: Compare against sector ETF compositions
3. **Historical Comparisons**: Track peer ranking changes over time
4. **Custom Sector Definitions**: User-defined peer groups
5. **Advanced Visualizations**: Interactive charts with plotly/matplotlib
6. **Machine Learning**: Predict peer relative performance

## Contributing

When contributing to this module:

1. Follow the project's Python style guide (Black, Ruff)
2. Add type hints to all functions
3. Include docstrings with examples
4. Write tests for new functionality
5. Update this README with new features

## License

Part of the AI Investment Agent project.
