"""
Backtesting framework for the AI Investment Agent.

This module provides a comprehensive backtesting system to evaluate
trading strategies and investment decisions using historical data.

Main Components:
    - BacktestEngine: Core backtesting engine for running simulations
    - HistoricalDataLoader: Loads and caches historical price data
    - SimulatedPortfolio: Tracks portfolio state during backtesting
    - BacktestReport: Generates performance reports and visualizations
    - Performance metrics: Sharpe ratio, Sortino ratio, max drawdown, etc.

Example:
    >>> from src.backtesting import BacktestEngine, HistoricalDataLoader
    >>>
    >>> loader = HistoricalDataLoader()
    >>> engine = BacktestEngine(
    ...     initial_capital=100000,
    ...     position_size=0.1,
    ...     data_loader=loader
    ... )
    >>>
    >>> result = engine.run_backtest(
    ...     ticker="AAPL",
    ...     start_date="2023-01-01",
    ...     end_date="2024-01-01"
    ... )
    >>>
    >>> print(result.summary())
"""

from src.backtesting.data_loader import HistoricalDataLoader
from src.backtesting.engine import BacktestEngine, BacktestConfig, BacktestResult
from src.backtesting.metrics import PerformanceMetrics
from src.backtesting.portfolio import SimulatedPortfolio, Position, Trade
from src.backtesting.reports import BacktestReport

__all__ = [
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "HistoricalDataLoader",
    "SimulatedPortfolio",
    "Position",
    "Trade",
    "PerformanceMetrics",
    "BacktestReport",
]

__version__ = "1.0.0"
