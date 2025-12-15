"""
Backtesting engine for the AI Investment Agent.

This module provides the core backtesting engine that simulates
trading strategies using historical data.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

import pandas as pd

from src.backtesting.data_loader import HistoricalDataLoader
from src.backtesting.metrics import PerformanceMetrics
from src.backtesting.portfolio import SimulatedPortfolio
from src.exceptions import DataValidationError, InvestmentAgentError

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """
    Configuration for backtesting.

    Attributes:
        initial_capital: Starting portfolio value
        position_size: Fraction of portfolio to allocate per trade (0.0 to 1.0)
        commission_rate: Commission rate as decimal (e.g., 0.001 for 0.1%)
        min_commission: Minimum commission per trade
        benchmark: Benchmark ticker for comparison (e.g., 'SPY')
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino calculations
        slippage: Price slippage as fraction (e.g., 0.001 for 0.1%)
    """

    initial_capital: float = 100000.0
    position_size: float = 0.1  # 10% of portfolio per trade
    commission_rate: float = 0.0  # No commission by default
    min_commission: float = 0.0
    benchmark: str = "SPY"
    risk_free_rate: float = 0.02
    slippage: float = 0.0  # No slippage by default

    def __post_init__(self):
        """Validate configuration."""
        if self.initial_capital <= 0:
            raise DataValidationError(
                "Initial capital must be positive",
                field="initial_capital",
                value=self.initial_capital,
                expected="> 0",
            )

        if not 0 < self.position_size <= 1:
            raise DataValidationError(
                "Position size must be between 0 and 1",
                field="position_size",
                value=self.position_size,
                expected="0 < value <= 1",
            )

        if self.commission_rate < 0:
            raise DataValidationError(
                "Commission rate cannot be negative",
                field="commission_rate",
                value=self.commission_rate,
                expected=">= 0",
            )

        if self.slippage < 0:
            raise DataValidationError(
                "Slippage cannot be negative",
                field="slippage",
                value=self.slippage,
                expected=">= 0",
            )


@dataclass
class BacktestResult:
    """
    Results from a backtest run.

    Attributes:
        ticker: Stock ticker tested
        start_date: Backtest start date
        end_date: Backtest end date
        config: Backtest configuration used
        portfolio: Final portfolio state
        metrics: Performance metrics
        equity_curve: Portfolio value over time
        returns: Period returns
        trades: Trade history
        benchmark_returns: Benchmark returns for comparison
    """

    ticker: str
    start_date: datetime
    end_date: datetime
    config: BacktestConfig
    portfolio: SimulatedPortfolio
    metrics: dict
    equity_curve: pd.Series
    returns: pd.Series
    trades: pd.DataFrame
    benchmark_returns: Optional[pd.Series] = None

    def summary(self) -> str:
        """Generate a text summary of backtest results."""
        lines = [
            "=" * 60,
            f"Backtest Results: {self.ticker}",
            f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            "=" * 60,
            "",
            "PERFORMANCE METRICS",
            "-" * 60,
            f"Total Return:       {self.metrics['total_return']:>10.2f}%",
            f"CAGR:               {self.metrics['cagr']:>10.2f}%",
            f"Sharpe Ratio:       {self.metrics['sharpe_ratio']:>10.2f}",
            f"Sortino Ratio:      {self.metrics['sortino_ratio']:>10.2f}",
            f"Calmar Ratio:       {self.metrics['calmar_ratio']:>10.2f}",
            "",
            "RISK METRICS",
            "-" * 60,
            f"Volatility:         {self.metrics['volatility']:>10.2f}%",
            f"Max Drawdown:       {self.metrics['max_drawdown']:>10.2f}%",
            "",
            "TRADE STATISTICS",
            "-" * 60,
            f"Total Trades:       {self.metrics['total_trades']:>10}",
            f"Win Rate:           {self.metrics['win_rate']:>10.2f}%",
            f"Winning Trades:     {self.metrics['num_wins']:>10}",
            f"Losing Trades:      {self.metrics['num_losses']:>10}",
            f"Profit Factor:      {self.metrics['profit_factor']:>10.2f}",
            "",
            "PORTFOLIO",
            "-" * 60,
            f"Initial Capital:    ${self.config.initial_capital:>10,.2f}",
            f"Final Value:        ${self.equity_curve.iloc[-1]:>10,.2f}",
            f"Total Commissions:  ${self.portfolio.get_total_commissions():>10,.2f}",
        ]

        # Add benchmark comparison if available
        if "benchmark" in self.metrics:
            bm = self.metrics["benchmark"]
            lines.extend(
                [
                    "",
                    "BENCHMARK COMPARISON",
                    "-" * 60,
                    f"Strategy Return:    {bm['strategy_cumulative_return']:>10.2f}%",
                    f"Benchmark Return:   {bm['benchmark_cumulative_return']:>10.2f}%",
                    f"Excess Return:      {bm['excess_return']:>10.2f}%",
                    f"Beta:               {bm['beta']:>10.2f}",
                    f"Alpha:              {bm['alpha']:>10.2f}%",
                    f"Correlation:        {bm['correlation']:>10.2f}",
                    f"Information Ratio:  {bm['information_ratio']:>10.2f}",
                ]
            )

        lines.append("=" * 60)
        return "\n".join(lines)


class BacktestEngine:
    """
    Core backtesting engine.

    This class orchestrates the backtesting process, including:
    - Loading historical data
    - Simulating trading signals
    - Executing trades through simulated portfolio
    - Calculating performance metrics
    - Generating reports

    Example:
        >>> engine = BacktestEngine(
        ...     config=BacktestConfig(initial_capital=100000)
        ... )
        >>>
        >>> # Define a simple strategy
        >>> def strategy(data, date):
        ...     # Buy when price crosses above 50-day MA
        ...     if data.loc[date, 'Close'] > data.loc[date, 'MA50']:
        ...         return 'BUY'
        ...     return 'SELL'
        >>>
        >>> result = engine.run_backtest(
        ...     ticker="AAPL",
        ...     start_date="2023-01-01",
        ...     end_date="2024-01-01",
        ...     strategy_func=strategy
        ... )
    """

    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        data_loader: Optional[HistoricalDataLoader] = None,
    ):
        """
        Initialize the backtest engine.

        Args:
            config: Backtest configuration (uses defaults if not provided)
            data_loader: Data loader instance (creates new one if not provided)
        """
        self.config = config or BacktestConfig()
        self.data_loader = data_loader or HistoricalDataLoader()
        self.metrics_calculator = PerformanceMetrics(
            risk_free_rate=self.config.risk_free_rate
        )

        logger.info(
            f"BacktestEngine initialized with ${self.config.initial_capital:,.2f} "
            f"initial capital"
        )

    def run_backtest(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        strategy_func: Optional[Callable] = None,
        signals: Optional[pd.Series] = None,
    ) -> BacktestResult:
        """
        Run a backtest for a ticker.

        Args:
            ticker: Stock ticker to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            strategy_func: Optional strategy function that returns signals
            signals: Optional pre-computed signals (overrides strategy_func)

        Returns:
            BacktestResult with complete results

        Raises:
            DataValidationError: If neither strategy_func nor signals provided
            InvestmentAgentError: If backtest fails

        Note:
            Either strategy_func or signals must be provided.
            strategy_func should accept (data, date) and return 'BUY', 'SELL', or 'HOLD'
        """
        if strategy_func is None and signals is None:
            raise DataValidationError(
                "Either strategy_func or signals must be provided",
                field="strategy",
                value="both None",
                expected="strategy_func or signals",
            )

        logger.info(f"Running backtest for {ticker} from {start_date} to {end_date}")

        try:
            # Load price data
            price_data = self.data_loader.load_price_data(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
            )

            # Generate or use provided signals
            if signals is None:
                trading_signals = self.simulate_signals(price_data, strategy_func)
            else:
                trading_signals = signals

            # Calculate returns and simulate trading
            portfolio, equity_curve, returns = self.calculate_returns(
                price_data=price_data,
                signals=trading_signals,
            )

            # Load benchmark data
            benchmark_returns = None
            if self.config.benchmark:
                try:
                    benchmark_data = self.data_loader.load_benchmark_data(
                        benchmark=self.config.benchmark,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    # Calculate benchmark returns
                    benchmark_returns = benchmark_data["Close"].pct_change().dropna()
                except Exception as e:
                    logger.warning(f"Failed to load benchmark data: {e}")

            # Calculate performance metrics
            metrics = self.metrics_calculator.calculate_all_metrics(
                equity_curve=equity_curve,
                returns=returns,
                trades=portfolio.get_trade_log(),
                benchmark_returns=benchmark_returns,
            )

            # Create result object
            result = BacktestResult(
                ticker=ticker,
                start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                end_date=datetime.strptime(end_date, "%Y-%m-%d"),
                config=self.config,
                portfolio=portfolio,
                metrics=metrics,
                equity_curve=equity_curve,
                returns=returns,
                trades=portfolio.get_trade_log(),
                benchmark_returns=benchmark_returns,
            )

            logger.info(f"Backtest completed: {result.metrics['total_return']:.2f}% return")

            return result

        except Exception as e:
            if isinstance(e, InvestmentAgentError):
                raise
            raise InvestmentAgentError(
                f"Backtest failed for {ticker}",
                details={"ticker": ticker, "start": start_date, "end": end_date},
                cause=e,
            ) from e

    def simulate_signals(
        self,
        price_data: pd.DataFrame,
        strategy_func: Callable,
    ) -> pd.Series:
        """
        Generate trading signals using a strategy function.

        Args:
            price_data: Historical price data
            strategy_func: Function that returns 'BUY', 'SELL', or 'HOLD'

        Returns:
            Series of trading signals indexed by date
        """
        logger.info("Simulating trading signals")

        signals = []
        dates = []

        for date in price_data.index:
            # Get signal from strategy function
            try:
                signal = strategy_func(price_data, date)
                signals.append(signal)
                dates.append(date)
            except Exception as e:
                logger.warning(f"Strategy function error at {date}: {e}")
                signals.append("HOLD")
                dates.append(date)

        signal_series = pd.Series(signals, index=dates)

        logger.info(
            f"Generated {len(signal_series)} signals: "
            f"{(signal_series == 'BUY').sum()} BUY, "
            f"{(signal_series == 'SELL').sum()} SELL, "
            f"{(signal_series == 'HOLD').sum()} HOLD"
        )

        return signal_series

    def calculate_returns(
        self,
        price_data: pd.DataFrame,
        signals: pd.Series,
    ) -> tuple[SimulatedPortfolio, pd.Series, pd.Series]:
        """
        Calculate returns by simulating trades based on signals.

        Args:
            price_data: Historical price data
            signals: Trading signals

        Returns:
            Tuple of (portfolio, equity_curve, returns)
        """
        logger.info("Calculating returns from signals")

        # Initialize portfolio
        portfolio = SimulatedPortfolio(
            initial_capital=self.config.initial_capital,
            commission_rate=self.config.commission_rate,
            min_commission=self.config.min_commission,
        )

        # Align signals with price data
        aligned_signals = signals.reindex(price_data.index, fill_value="HOLD")

        # Track equity values
        equity_values = []
        dates = []

        # Simulate trading day by day
        for date in price_data.index:
            signal = aligned_signals[date]
            close_price = price_data.loc[date, "Close"]

            # Apply slippage to execution price
            if self.config.slippage > 0:
                if signal == "BUY":
                    execution_price = close_price * (1 + self.config.slippage)
                elif signal == "SELL":
                    execution_price = close_price * (1 - self.config.slippage)
                else:
                    execution_price = close_price
            else:
                execution_price = close_price

            # Execute trade based on signal
            ticker = price_data.index.name if price_data.index.name else "STOCK"
            portfolio.execute_trade(
                ticker=ticker,
                signal=signal,
                price=execution_price,
                date=date,
                position_size=self.config.position_size,
            )

            # Update prices for existing positions
            prices = {ticker: close_price}
            portfolio.update_prices(prices, date)

            # Record portfolio value
            portfolio_value = portfolio.get_portfolio_value(date)
            equity_values.append(portfolio_value)
            dates.append(date)

        # Create equity curve
        equity_curve = pd.Series(equity_values, index=dates)

        # Calculate returns
        returns = equity_curve.pct_change().dropna()

        logger.info(
            f"Simulation complete: {len(portfolio.trades)} trades executed, "
            f"final value ${equity_curve.iloc[-1]:,.2f}"
        )

        return portfolio, equity_curve, returns

    def run_multiple_backtests(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        strategy_func: Optional[Callable] = None,
    ) -> Dict[str, BacktestResult]:
        """
        Run backtests for multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            strategy_func: Strategy function

        Returns:
            Dictionary mapping ticker to BacktestResult
        """
        logger.info(f"Running backtests for {len(tickers)} tickers")

        results = {}

        for ticker in tickers:
            try:
                result = self.run_backtest(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    strategy_func=strategy_func,
                )
                results[ticker] = result
                logger.info(f"Completed backtest for {ticker}")
            except Exception as e:
                logger.error(f"Failed to backtest {ticker}: {e}")
                continue

        logger.info(f"Completed {len(results)}/{len(tickers)} backtests")

        return results

    def optimize_parameters(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        strategy_func: Callable,
        param_grid: Dict[str, List],
    ) -> Dict:
        """
        Optimize strategy parameters using grid search.

        Args:
            ticker: Stock ticker to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            strategy_func: Strategy function that accepts parameters
            param_grid: Dictionary of parameter names to lists of values

        Returns:
            Dictionary with best parameters and results

        Example:
            >>> param_grid = {
            ...     'ma_short': [10, 20, 30],
            ...     'ma_long': [50, 100, 200]
            ... }
            >>> best = engine.optimize_parameters(
            ...     ticker="AAPL",
            ...     start_date="2023-01-01",
            ...     end_date="2024-01-01",
            ...     strategy_func=ma_crossover_strategy,
            ...     param_grid=param_grid
            ... )
        """
        logger.info(f"Optimizing parameters for {ticker}")

        # Generate all parameter combinations
        from itertools import product

        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))

        best_result = None
        best_params = None
        best_sharpe = float("-inf")

        for combo in combinations:
            params = dict(zip(param_names, combo))
            logger.debug(f"Testing parameters: {params}")

            try:
                # Create strategy function with these parameters
                def parameterized_strategy(data, date):
                    return strategy_func(data, date, **params)

                # Run backtest
                result = self.run_backtest(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    strategy_func=parameterized_strategy,
                )

                # Check if this is the best result
                sharpe = result.metrics["sharpe_ratio"]
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_result = result
                    best_params = params

            except Exception as e:
                logger.warning(f"Failed to test parameters {params}: {e}")
                continue

        logger.info(f"Best parameters: {best_params} (Sharpe: {best_sharpe:.2f})")

        return {
            "best_params": best_params,
            "best_result": best_result,
            "best_sharpe": best_sharpe,
            "total_combinations": len(combinations),
        }
