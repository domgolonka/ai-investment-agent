"""
Example demonstrating the backtesting framework.

This script shows how to:
1. Create a simple trading strategy
2. Run a backtest
3. Generate reports
4. Compare with benchmark
"""

import logging
from datetime import datetime

import pandas as pd

from src.backtesting import (
    BacktestEngine,
    BacktestConfig,
    HistoricalDataLoader,
    BacktestReport,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def simple_ma_crossover_strategy(data: pd.DataFrame, date: pd.Timestamp) -> str:
    """
    Simple moving average crossover strategy.

    Buy when short MA crosses above long MA.
    Sell when short MA crosses below long MA.

    Args:
        data: Historical price data with MA columns
        date: Current date

    Returns:
        'BUY', 'SELL', or 'HOLD'
    """
    # Need at least 50 days of data
    if len(data[:date]) < 50:
        return "HOLD"

    # Calculate moving averages if not already present
    if "MA20" not in data.columns:
        data["MA20"] = data["Close"].rolling(window=20).mean()
        data["MA50"] = data["Close"].rolling(window=50).mean()

    current_idx = data.index.get_loc(date)

    # Can't trade on first day or if MAs not available
    if current_idx == 0 or pd.isna(data.loc[date, "MA20"]):
        return "HOLD"

    prev_date = data.index[current_idx - 1]

    # Get current and previous MA values
    current_ma20 = data.loc[date, "MA20"]
    current_ma50 = data.loc[date, "MA50"]
    prev_ma20 = data.loc[prev_date, "MA20"]
    prev_ma50 = data.loc[prev_date, "MA50"]

    # Check for crossover
    if prev_ma20 <= prev_ma50 and current_ma20 > current_ma50:
        return "BUY"
    elif prev_ma20 >= prev_ma50 and current_ma20 < current_ma50:
        return "SELL"
    else:
        return "HOLD"


def momentum_strategy(data: pd.DataFrame, date: pd.Timestamp) -> str:
    """
    Simple momentum strategy based on recent returns.

    Buy when momentum is positive, sell when negative.

    Args:
        data: Historical price data
        date: Current date

    Returns:
        'BUY', 'SELL', or 'HOLD'
    """
    lookback = 20  # 20-day momentum

    current_idx = data.index.get_loc(date)

    if current_idx < lookback:
        return "HOLD"

    # Calculate momentum
    current_price = data.loc[date, "Close"]
    past_price = data.iloc[current_idx - lookback]["Close"]
    momentum = (current_price - past_price) / past_price

    # Buy if positive momentum, sell if negative
    if momentum > 0.02:  # 2% threshold
        return "BUY"
    elif momentum < -0.02:
        return "SELL"
    else:
        return "HOLD"


def run_single_backtest():
    """Run a single backtest example."""
    logger.info("=" * 60)
    logger.info("EXAMPLE 1: Single Backtest with MA Crossover Strategy")
    logger.info("=" * 60)

    # Configure backtest
    config = BacktestConfig(
        initial_capital=100000.0,
        position_size=0.5,  # 50% of portfolio per trade
        commission_rate=0.001,  # 0.1% commission
        min_commission=1.0,
        benchmark="SPY",
        risk_free_rate=0.02,
    )

    # Create engine
    engine = BacktestEngine(config=config)

    # Run backtest
    result = engine.run_backtest(
        ticker="AAPL",
        start_date="2023-01-01",
        end_date="2024-01-01",
        strategy_func=simple_ma_crossover_strategy,
    )

    # Print summary
    print("\n" + result.summary())

    # Generate report
    report = BacktestReport(result)

    # Export results
    report.export_results("backtest_results/aapl_ma_crossover", format="json")
    report.export_results("backtest_results/aapl_ma_crossover", format="csv")

    # Generate HTML report
    BacktestReport.generate_report_html(
        result, "backtest_results/aapl_ma_crossover.html"
    )

    logger.info("\nReports generated successfully!")


def run_multiple_backtests():
    """Run backtests for multiple tickers."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 2: Multiple Backtests")
    logger.info("=" * 60)

    # Configure backtest
    config = BacktestConfig(
        initial_capital=100000.0,
        position_size=0.3,
        commission_rate=0.001,
    )

    # Create engine
    engine = BacktestEngine(config=config)

    # Run backtests for multiple tickers
    tickers = ["AAPL", "MSFT", "GOOGL"]

    results = engine.run_multiple_backtests(
        tickers=tickers,
        start_date="2023-01-01",
        end_date="2024-01-01",
        strategy_func=momentum_strategy,
    )

    # Compare results
    comparison = BacktestReport.compare_backtests(
        results, output_path="backtest_results/comparison.csv"
    )

    print("\n" + "=" * 60)
    print("COMPARISON OF STRATEGIES")
    print("=" * 60)
    print(comparison.to_string(index=False))


def run_parameter_optimization():
    """Run parameter optimization example."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 3: Parameter Optimization")
    logger.info("=" * 60)

    # Define parameterized strategy
    def ma_strategy_with_params(
        data: pd.DataFrame, date: pd.Timestamp, short_window: int, long_window: int
    ) -> str:
        """MA crossover with configurable windows."""
        if len(data[:date]) < long_window:
            return "HOLD"

        # Calculate MAs
        ma_short = data["Close"].rolling(window=short_window).mean()
        ma_long = data["Close"].rolling(window=long_window).mean()

        current_idx = data.index.get_loc(date)
        if current_idx == 0 or pd.isna(ma_short.loc[date]):
            return "HOLD"

        prev_date = data.index[current_idx - 1]

        # Check for crossover
        if ma_short.loc[prev_date] <= ma_long.loc[prev_date] and ma_short.loc[
            date
        ] > ma_long.loc[date]:
            return "BUY"
        elif ma_short.loc[prev_date] >= ma_long.loc[prev_date] and ma_short.loc[
            date
        ] < ma_long.loc[date]:
            return "SELL"
        else:
            return "HOLD"

    # Configure backtest
    config = BacktestConfig(initial_capital=100000.0, position_size=0.5)

    engine = BacktestEngine(config=config)

    # Define parameter grid
    param_grid = {
        "short_window": [10, 20, 30],
        "long_window": [50, 100, 200],
    }

    # Run optimization
    optimization_results = engine.optimize_parameters(
        ticker="AAPL",
        start_date="2023-01-01",
        end_date="2024-01-01",
        strategy_func=ma_strategy_with_params,
        param_grid=param_grid,
    )

    print("\n" + "=" * 60)
    print("PARAMETER OPTIMIZATION RESULTS")
    print("=" * 60)
    print(f"Best Parameters: {optimization_results['best_params']}")
    print(f"Best Sharpe Ratio: {optimization_results['best_sharpe']:.2f}")
    print(f"Combinations Tested: {optimization_results['total_combinations']}")

    if optimization_results["best_result"]:
        print("\nBest Strategy Performance:")
        print(optimization_results["best_result"].summary())


def demonstrate_data_loader():
    """Demonstrate data loader features."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 4: Data Loader Features")
    logger.info("=" * 60)

    loader = HistoricalDataLoader()

    # Load data
    data = loader.load_price_data(
        ticker="AAPL", start_date="2023-01-01", end_date="2024-01-01"
    )

    print(f"\nLoaded {len(data)} days of data for AAPL")
    print(f"Date range: {data.index.min()} to {data.index.max()}")
    print(f"\nFirst 5 rows:")
    print(data.head())

    # Resample to weekly
    weekly_data = loader.resample_data(data, "W")
    print(f"\nResampled to weekly: {len(weekly_data)} weeks")

    # Load benchmark
    benchmark = loader.load_benchmark_data(
        benchmark="SPY", start_date="2023-01-01", end_date="2024-01-01"
    )

    print(f"\nLoaded benchmark data: {len(benchmark)} days")

    # Align data
    aligned_aapl, aligned_spy = loader.align_data(data, benchmark)
    print(f"\nAligned data: {len(aligned_aapl)} common dates")


def main():
    """Run all examples."""
    try:
        # Example 1: Single backtest
        run_single_backtest()

        # Example 2: Multiple backtests
        run_multiple_backtests()

        # Example 3: Parameter optimization
        run_parameter_optimization()

        # Example 4: Data loader features
        demonstrate_data_loader()

        logger.info("\n" + "=" * 60)
        logger.info("All examples completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
