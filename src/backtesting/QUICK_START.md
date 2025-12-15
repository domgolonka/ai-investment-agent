# Backtesting Framework - Quick Start Guide

## 5-Minute Quick Start

### 1. Import the Framework

```python
from src.backtesting import BacktestEngine, BacktestConfig, BacktestReport
```

### 2. Define Your Strategy

```python
def my_strategy(data, date):
    """
    Your strategy logic here.

    Args:
        data: DataFrame with OHLCV data up to current date
        date: Current date being evaluated

    Returns:
        'BUY', 'SELL', or 'HOLD'
    """
    # Example: Buy if price > 50-day average
    if len(data[:date]) < 50:
        return 'HOLD'

    avg_price = data[:date]['Close'].tail(50).mean()
    current_price = data.loc[date, 'Close']

    if current_price > avg_price:
        return 'BUY'
    elif current_price < avg_price * 0.95:  # Sell if drops 5%
        return 'SELL'

    return 'HOLD'
```

### 3. Configure and Run

```python
# Configure backtest
config = BacktestConfig(
    initial_capital=100000,      # $100k starting capital
    position_size=0.1,           # Use 10% per trade
    commission_rate=0.001,       # 0.1% commission
    benchmark='SPY'              # Compare vs S&P 500
)

# Create engine
engine = BacktestEngine(config=config)

# Run backtest
result = engine.run_backtest(
    ticker='AAPL',
    start_date='2023-01-01',
    end_date='2024-01-01',
    strategy_func=my_strategy
)
```

### 4. View Results

```python
# Print summary
print(result.summary())

# Generate report
report = BacktestReport(result)
report.export_results('my_backtest', format='json')
```

## Common Use Cases

### Use Case 1: Test Multiple Tickers

```python
tickers = ['AAPL', 'MSFT', 'GOOGL']
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

### Use Case 2: Optimize Parameters

```python
def parameterized_strategy(data, date, threshold):
    # Your strategy with parameter
    pass

param_grid = {'threshold': [0.02, 0.05, 0.10]}

results = engine.optimize_parameters(
    ticker='AAPL',
    start_date='2023-01-01',
    end_date='2024-01-01',
    strategy_func=parameterized_strategy,
    param_grid=param_grid
)

print(f"Best: {results['best_params']}")
```

### Use Case 3: Export to Excel

```python
report = BacktestReport(result)
report.export_results('backtest_report', format='excel')
# Creates: backtest_report.xlsx with multiple sheets
```

## Key Metrics Explained

| Metric | What It Means | Good Value |
|--------|---------------|------------|
| **Total Return** | Overall gain/loss | > 0% |
| **CAGR** | Annualized return | > 10% |
| **Sharpe Ratio** | Return per unit risk | > 1.0 |
| **Max Drawdown** | Worst loss from peak | < 20% |
| **Win Rate** | % of profitable trades | > 50% |

## Configuration Options

```python
BacktestConfig(
    initial_capital=100000.0,    # Starting money
    position_size=0.1,           # 0.1 = 10% of portfolio per trade
    commission_rate=0.001,       # 0.001 = 0.1% commission
    min_commission=1.0,          # Minimum $1 per trade
    benchmark='SPY',             # Ticker to compare against
    risk_free_rate=0.02,         # 2% annual risk-free rate
    slippage=0.001               # 0.1% price slippage
)
```

## Strategy Function Template

```python
def strategy_template(data, date):
    """
    Template for strategy function.

    Available data columns:
    - data['Open']
    - data['High']
    - data['Low']
    - data['Close']
    - data['Volume']

    You can add indicators:
    - data['MA50'] = data['Close'].rolling(50).mean()
    - data['RSI'] = calculate_rsi(data['Close'])
    """

    # 1. Check if we have enough data
    if len(data[:date]) < minimum_bars:
        return 'HOLD'

    # 2. Calculate indicators (if not already done)
    if 'indicator' not in data.columns:
        data['indicator'] = calculate_indicator(data)

    # 3. Get current values
    current_idx = data.index.get_loc(date)
    current_value = data.loc[date, 'indicator']

    # 4. Make decision
    if buy_condition:
        return 'BUY'
    elif sell_condition:
        return 'SELL'
    else:
        return 'HOLD'
```

## Troubleshooting

### Issue: "No module named 'pandas'"
**Solution:** Install dependencies
```bash
poetry install
```

### Issue: "DataFetchError"
**Solution:** Check ticker symbol and date range
```python
# Verify ticker exists
loader = HistoricalDataLoader()
data = loader.load_price_data('AAPL', '2024-01-01', '2024-01-31')
```

### Issue: "Insufficient data for backtest"
**Solution:** Extend date range or reduce lookback period

### Issue: "No trades executed"
**Solution:** Check strategy is returning 'BUY' signals
```python
# Debug your strategy
signals = []
for date in data.index:
    signal = my_strategy(data, date)
    signals.append(signal)
print(pd.Series(signals).value_counts())
```

## Example Output

```
============================================================
Backtest Results: AAPL
Period: 2023-01-01 to 2024-01-01
============================================================

PERFORMANCE METRICS
------------------------------------------------------------
Total Return:            45.23%
CAGR:                    45.23%
Sharpe Ratio:             1.85
Sortino Ratio:            2.34
Calmar Ratio:             3.21

RISK METRICS
------------------------------------------------------------
Volatility:              18.45%
Max Drawdown:            14.08%

TRADE STATISTICS
------------------------------------------------------------
Total Trades:                12
Win Rate:                 66.67%
Winning Trades:                8
Losing Trades:                 4
Profit Factor:             2.15

BENCHMARK COMPARISON
------------------------------------------------------------
Strategy Return:         45.23%
Benchmark Return:        28.50%
Excess Return:           16.73%
Beta:                     0.95
Alpha:                    2.34%
```

## Next Steps

1. **Read Full Documentation**: `src/backtesting/README.md`
2. **Run Examples**: `python examples/backtest_example.py`
3. **Run Tests**: `pytest tests/test_backtesting.py`
4. **Implement Your Strategy**: Start with template above
5. **Optimize**: Use parameter grid search

## Getting Help

- Check `src/backtesting/README.md` for detailed docs
- See `examples/backtest_example.py` for working examples
- Review `tests/test_backtesting.py` for usage patterns
- Read `BACKTESTING_IMPLEMENTATION.md` for architecture details

Happy Backtesting! 🚀
