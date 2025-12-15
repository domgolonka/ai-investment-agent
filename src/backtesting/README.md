# Backtesting Framework

A comprehensive backtesting framework for the AI Investment Agent that enables rigorous evaluation of trading strategies using historical data.

## Features

- **Complete Backtesting Engine**: Simulate trading strategies with realistic execution
- **Historical Data Management**: Load, cache, and validate historical price data
- **Portfolio Simulation**: Track positions, cash, and trades with commission modeling
- **Performance Metrics**: Calculate Sharpe ratio, Sortino ratio, max drawdown, CAGR, and more
- **Benchmark Comparison**: Compare strategy performance against market benchmarks
- **Flexible Reporting**: Export results to JSON, CSV, Excel, and HTML formats
- **Parameter Optimization**: Grid search for optimal strategy parameters

## Installation

The backtesting framework is included in the main project. Ensure you have the required dependencies:

```bash
poetry install
```

Required packages:
- `pandas` - Data manipulation
- `numpy` - Numerical computations
- `yfinance` - Historical price data
- `openpyxl` - Excel export (optional)

## Quick Start

```python
from src.backtesting import BacktestEngine, BacktestConfig

# Define a simple strategy
def my_strategy(data, date):
    # Your strategy logic here
    if some_buy_condition:
        return 'BUY'
    elif some_sell_condition:
        return 'SELL'
    else:
        return 'HOLD'

# Configure and run backtest
config = BacktestConfig(
    initial_capital=100000,
    position_size=0.1,  # 10% per trade
    commission_rate=0.001,  # 0.1%
    benchmark='SPY'
)

engine = BacktestEngine(config=config)

result = engine.run_backtest(
    ticker='AAPL',
    start_date='2023-01-01',
    end_date='2024-01-01',
    strategy_func=my_strategy
)

# View results
print(result.summary())
```

## Architecture

### Core Components

#### 1. BacktestEngine (`engine.py`)

The main orchestrator that runs backtests.

**Key Methods:**
- `run_backtest()` - Execute a backtest for a single ticker
- `simulate_signals()` - Generate trading signals from strategy function
- `calculate_returns()` - Compute portfolio returns from signals
- `run_multiple_backtests()` - Test multiple tickers
- `optimize_parameters()` - Grid search for best parameters

#### 2. HistoricalDataLoader (`data_loader.py`)

Manages historical price data with caching.

**Key Methods:**
- `load_price_data()` - Load OHLCV data from yfinance
- `load_benchmark_data()` - Load benchmark for comparison
- `resample_data()` - Change timeframe (daily to weekly, etc.)
- `clear_cache()` - Manage cached data

**Features:**
- Automatic caching to avoid repeated API calls
- Data validation (OHLC consistency, missing values)
- Support for different timeframes

#### 3. SimulatedPortfolio (`portfolio.py`)

Tracks portfolio state during backtesting.

**Key Methods:**
- `execute_trade()` - Execute buy/sell orders
- `get_portfolio_value()` - Calculate total value
- `get_holdings()` - View current positions
- `update_prices()` - Update position values

**Features:**
- Commission modeling
- Position tracking with average cost basis
- Complete trade history
- P&L calculation

#### 4. PerformanceMetrics (`metrics.py`)

Calculates comprehensive performance metrics.

**Key Methods:**
- `calculate_sharpe_ratio()` - Risk-adjusted returns
- `calculate_sortino_ratio()` - Downside risk-adjusted returns
- `calculate_max_drawdown()` - Worst peak-to-trough decline
- `calculate_cagr()` - Compound annual growth rate
- `calculate_win_rate()` - Percentage of winning trades
- `compare_to_benchmark()` - Compare with market index

**Metrics Provided:**
- Total return and CAGR
- Risk metrics (Sharpe, Sortino, Calmar)
- Drawdown analysis
- Trade statistics (win rate, profit factor)
- Benchmark comparison (alpha, beta, correlation)

#### 5. BacktestReport (`reports.py`)

Generates reports and exports results.

**Key Methods:**
- `generate_summary()` - Text summary of results
- `generate_equity_curve()` - Portfolio value over time
- `generate_trade_log()` - Detailed trade history
- `export_results()` - Save to JSON/CSV/Excel
- `compare_backtests()` - Compare multiple strategies

**Export Formats:**
- JSON - Structured data with metadata
- CSV - Multiple files (equity, trades, returns)
- Excel - Multi-sheet workbook
- HTML - Visual report in browser

## Configuration

### BacktestConfig

```python
@dataclass
class BacktestConfig:
    initial_capital: float = 100000.0      # Starting capital
    position_size: float = 0.1             # Fraction per trade (0-1)
    commission_rate: float = 0.0           # Commission as decimal
    min_commission: float = 0.0            # Minimum per trade
    benchmark: str = "SPY"                 # Benchmark ticker
    risk_free_rate: float = 0.02           # For Sharpe/Sortino
    slippage: float = 0.0                  # Price slippage
```

### DataLoaderConfig

```python
@dataclass
class DataLoaderConfig:
    cache_dir: Path = Path("data/backtest_cache")
    cache_enabled: bool = True
    auto_adjust: bool = True               # Adjust for splits/dividends
    validate_data: bool = True
    min_data_points: int = 20
```

## Usage Examples

### Example 1: Moving Average Crossover

```python
def ma_crossover_strategy(data, date):
    """Buy when 20-day MA crosses above 50-day MA."""
    if 'MA20' not in data.columns:
        data['MA20'] = data['Close'].rolling(20).mean()
        data['MA50'] = data['Close'].rolling(50).mean()

    current_idx = data.index.get_loc(date)
    if current_idx == 0:
        return 'HOLD'

    prev_date = data.index[current_idx - 1]

    if (data.loc[prev_date, 'MA20'] <= data.loc[prev_date, 'MA50'] and
        data.loc[date, 'MA20'] > data.loc[date, 'MA50']):
        return 'BUY'
    elif (data.loc[prev_date, 'MA20'] >= data.loc[prev_date, 'MA50'] and
          data.loc[date, 'MA20'] < data.loc[date, 'MA50']):
        return 'SELL'

    return 'HOLD'

# Run backtest
engine = BacktestEngine()
result = engine.run_backtest(
    ticker='AAPL',
    start_date='2023-01-01',
    end_date='2024-01-01',
    strategy_func=ma_crossover_strategy
)
```

### Example 2: Momentum Strategy

```python
def momentum_strategy(data, date):
    """Buy if 20-day return > 5%, sell if < -5%."""
    lookback = 20
    current_idx = data.index.get_loc(date)

    if current_idx < lookback:
        return 'HOLD'

    current_price = data.loc[date, 'Close']
    past_price = data.iloc[current_idx - lookback]['Close']
    momentum = (current_price - past_price) / past_price

    if momentum > 0.05:
        return 'BUY'
    elif momentum < -0.05:
        return 'SELL'

    return 'HOLD'
```

### Example 3: Using Pre-computed Signals

```python
# Generate signals separately
signals = pd.Series(index=price_data.index)
signals[:] = 'HOLD'
signals[buy_conditions] = 'BUY'
signals[sell_conditions] = 'SELL'

# Run backtest with signals
result = engine.run_backtest(
    ticker='AAPL',
    start_date='2023-01-01',
    end_date='2024-01-01',
    signals=signals
)
```

### Example 4: Parameter Optimization

```python
def ma_strategy_params(data, date, short_window, long_window):
    """Parameterized MA crossover."""
    # Strategy logic using parameters
    pass

param_grid = {
    'short_window': [10, 20, 30],
    'long_window': [50, 100, 200]
}

results = engine.optimize_parameters(
    ticker='AAPL',
    start_date='2023-01-01',
    end_date='2024-01-01',
    strategy_func=ma_strategy_params,
    param_grid=param_grid
)

print(f"Best params: {results['best_params']}")
print(f"Best Sharpe: {results['best_sharpe']:.2f}")
```

### Example 5: Multiple Backtests

```python
# Test same strategy on multiple tickers
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

results = engine.run_multiple_backtests(
    tickers=tickers,
    start_date='2023-01-01',
    end_date='2024-01-01',
    strategy_func=my_strategy
)

# Compare results
comparison = BacktestReport.compare_backtests(results)
print(comparison)
```

### Example 6: Export Results

```python
report = BacktestReport(result)

# Export to JSON
report.export_results('results/my_backtest', format='json')

# Export to CSV (creates directory with multiple files)
report.export_results('results/my_backtest', format='csv')

# Export to Excel (multi-sheet workbook)
report.export_results('results/my_backtest', format='excel')

# Generate HTML report
BacktestReport.generate_report_html(result, 'results/report.html')
```

## Performance Metrics Explained

### Return Metrics

- **Total Return**: Overall percentage gain/loss
- **CAGR**: Compound annual growth rate (annualized return)

### Risk-Adjusted Returns

- **Sharpe Ratio**: (Return - Risk Free Rate) / Volatility
  - Higher is better (>1 is good, >2 is excellent)
  - Measures return per unit of risk

- **Sortino Ratio**: (Return - Target) / Downside Deviation
  - Similar to Sharpe but only considers downside volatility
  - Better for asymmetric return distributions

- **Calmar Ratio**: CAGR / Max Drawdown
  - Measures return relative to worst drawdown

### Risk Metrics

- **Volatility**: Standard deviation of returns (annualized)
- **Max Drawdown**: Largest peak-to-trough decline
- **Beta**: Sensitivity to benchmark movements
- **Alpha**: Excess return vs. benchmark (adjusted for beta)

### Trade Statistics

- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Information Ratio**: Excess return / Tracking error
- **Tracking Error**: Deviation from benchmark

## Best Practices

### Strategy Development

1. **Start Simple**: Begin with basic strategies before adding complexity
2. **Avoid Overfitting**: Test on out-of-sample data
3. **Consider Transaction Costs**: Include realistic commissions and slippage
4. **Handle Edge Cases**: Ensure strategy works at start/end of data
5. **Document Assumptions**: Clearly state strategy logic and parameters

### Data Management

1. **Cache Data**: Enable caching to avoid repeated API calls
2. **Validate Data**: Always validate data quality
3. **Handle Missing Data**: Account for gaps in historical data
4. **Adjust for Corporate Actions**: Use auto-adjust for splits/dividends

### Performance Analysis

1. **Use Multiple Metrics**: Don't rely on a single metric
2. **Compare to Benchmark**: Always benchmark against relevant index
3. **Analyze Drawdowns**: Understand when and why losses occurred
4. **Check Trade Distribution**: Ensure sufficient number of trades
5. **Walk-Forward Testing**: Test on rolling windows

### Common Pitfalls

1. **Look-Ahead Bias**: Don't use future information
2. **Survivorship Bias**: Include delisted stocks when possible
3. **Data Snooping**: Avoid testing too many parameters
4. **Unrealistic Execution**: Model slippage and commissions
5. **Ignoring Market Regime**: Test across different market conditions

## Integration with AI Investment Agent

The backtesting framework integrates with the AI Investment Agent to:

1. **Validate Agent Decisions**: Test historical performance of agent recommendations
2. **Tune Parameters**: Optimize agent configuration settings
3. **Risk Assessment**: Understand potential drawdowns and volatility
4. **Strategy Comparison**: Compare AI agent vs. traditional strategies
5. **Performance Attribution**: Identify which decisions added value

Example integration:

```python
from src.agents import InvestmentAgent
from src.backtesting import BacktestEngine

# Create agent-based strategy
agent = InvestmentAgent()

def agent_strategy(data, date):
    # Get agent recommendation
    analysis = agent.analyze(ticker, data[:date])
    return analysis.recommendation  # 'BUY', 'SELL', 'HOLD'

# Backtest agent performance
result = engine.run_backtest(
    ticker='AAPL',
    start_date='2023-01-01',
    end_date='2024-01-01',
    strategy_func=agent_strategy
)
```

## File Structure

```
src/backtesting/
├── __init__.py          # Package exports
├── engine.py            # BacktestEngine class
├── data_loader.py       # HistoricalDataLoader class
├── portfolio.py         # SimulatedPortfolio, Trade, Position
├── metrics.py           # PerformanceMetrics class
├── reports.py           # BacktestReport class
└── README.md           # This file

examples/
└── backtest_example.py  # Usage examples

data/
└── backtest_cache/      # Cached historical data
```

## Contributing

When adding features to the backtesting framework:

1. Maintain type hints for all functions
2. Add comprehensive docstrings
3. Include unit tests
4. Update this README with examples
5. Use the existing exception hierarchy from `src/exceptions.py`

## License

This backtesting framework is part of the AI Investment Agent project and follows the same license.

## Support

For issues or questions:
1. Check the examples in `examples/backtest_example.py`
2. Review this README
3. Open an issue on the project repository

## Changelog

### Version 1.0.0 (2024-12-14)
- Initial release
- Complete backtesting engine
- Historical data loader with caching
- Portfolio simulation
- Comprehensive performance metrics
- Multiple export formats
- Parameter optimization
