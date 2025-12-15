"""
Performance metrics for backtesting.

This module provides comprehensive performance metrics to evaluate
backtesting results including risk-adjusted returns, drawdowns,
and benchmark comparisons.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from src.exceptions import DataValidationError

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """
    Comprehensive performance metrics for backtesting results.

    This class calculates various performance metrics including:
    - Risk-adjusted returns (Sharpe, Sortino)
    - Drawdown metrics
    - Win/loss statistics
    - Annualized returns
    - Volatility measures

    Example:
        >>> metrics = PerformanceMetrics()
        >>> sharpe = metrics.calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        >>> max_dd = metrics.calculate_max_drawdown(equity_curve)
    """

    risk_free_rate: float = 0.02  # Annual risk-free rate (2% default)
    trading_days_per_year: int = 252

    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: Optional[float] = None,
    ) -> float:
        """
        Calculate Sharpe ratio.

        The Sharpe ratio measures risk-adjusted return by comparing
        excess returns to volatility.

        Args:
            returns: Series of period returns
            risk_free_rate: Annual risk-free rate (uses default if None)

        Returns:
            Sharpe ratio (annualized)

        Formula:
            Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
            Then annualized: Sharpe * sqrt(252)
        """
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        if len(returns) < 2:
            logger.warning("Insufficient data for Sharpe ratio calculation")
            return 0.0

        # Convert annual risk-free rate to period rate
        period_rf_rate = risk_free_rate / self.trading_days_per_year

        # Calculate excess returns
        excess_returns = returns - period_rf_rate

        # Calculate Sharpe ratio
        if excess_returns.std() == 0:
            return 0.0

        sharpe = excess_returns.mean() / excess_returns.std()

        # Annualize
        sharpe_annual = sharpe * np.sqrt(self.trading_days_per_year)

        return sharpe_annual

    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: Optional[float] = None,
        target_return: float = 0.0,
    ) -> float:
        """
        Calculate Sortino ratio.

        Similar to Sharpe ratio but only considers downside volatility,
        making it more appropriate for strategies with asymmetric returns.

        Args:
            returns: Series of period returns
            risk_free_rate: Annual risk-free rate (uses default if None)
            target_return: Minimum acceptable return (default 0)

        Returns:
            Sortino ratio (annualized)

        Formula:
            Sortino = (Mean Return - Target Return) / Downside Deviation
            Then annualized: Sortino * sqrt(252)
        """
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        if len(returns) < 2:
            logger.warning("Insufficient data for Sortino ratio calculation")
            return 0.0

        # Calculate downside returns (only negative returns)
        downside_returns = returns[returns < target_return]

        if len(downside_returns) == 0:
            # No downside volatility - perfect performance
            return np.inf if returns.mean() > target_return else 0.0

        # Calculate downside deviation
        downside_std = downside_returns.std()

        if downside_std == 0:
            return 0.0

        # Calculate Sortino ratio
        sortino = (returns.mean() - target_return) / downside_std

        # Annualize
        sortino_annual = sortino * np.sqrt(self.trading_days_per_year)

        return sortino_annual

    def calculate_max_drawdown(
        self,
        equity_curve: pd.Series,
    ) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """
        Calculate maximum drawdown.

        Maximum drawdown is the largest peak-to-trough decline in
        portfolio value, expressed as a percentage.

        Args:
            equity_curve: Series of portfolio values over time

        Returns:
            Tuple of (max_drawdown_pct, peak_date, trough_date)

        Example:
            >>> max_dd, peak, trough = metrics.calculate_max_drawdown(portfolio_values)
            >>> print(f"Max drawdown: {max_dd:.2f}% from {peak} to {trough}")
        """
        if len(equity_curve) < 2:
            logger.warning("Insufficient data for max drawdown calculation")
            return 0.0, None, None

        # Calculate running maximum
        running_max = equity_curve.expanding().max()

        # Calculate drawdown at each point
        drawdown = (equity_curve - running_max) / running_max

        # Find maximum drawdown
        max_drawdown_idx = drawdown.idxmin()
        max_drawdown_pct = drawdown[max_drawdown_idx] * 100

        # Find peak (date when running max was achieved before the drawdown)
        peak_idx = equity_curve[:max_drawdown_idx].idxmax()

        return abs(max_drawdown_pct), peak_idx, max_drawdown_idx

    def calculate_drawdown_series(
        self,
        equity_curve: pd.Series,
    ) -> pd.Series:
        """
        Calculate drawdown at each point in time.

        Args:
            equity_curve: Series of portfolio values over time

        Returns:
            Series of drawdown percentages over time
        """
        running_max = equity_curve.expanding().max()
        drawdown = ((equity_curve - running_max) / running_max) * 100
        return drawdown

    def calculate_win_rate(
        self,
        trades: pd.DataFrame,
    ) -> Tuple[float, int, int]:
        """
        Calculate win rate from trade history.

        Args:
            trades: DataFrame with trade history containing 'direction',
                   'price', and 'shares' columns

        Returns:
            Tuple of (win_rate_pct, num_wins, num_losses)
        """
        if trades.empty or len(trades) < 2:
            logger.warning("Insufficient trades for win rate calculation")
            return 0.0, 0, 0

        # Group trades by ticker to calculate round-trip P&L
        winning_trades = 0
        losing_trades = 0

        # Track positions by ticker
        positions = {}

        for _, trade in trades.iterrows():
            ticker = trade["ticker"]
            direction = trade["direction"]
            price = trade["price"]
            shares = trade["shares"]

            if ticker not in positions:
                positions[ticker] = {"shares": 0, "avg_price": 0, "cost_basis": 0}

            pos = positions[ticker]

            if direction == "BUY":
                # Add to position
                total_cost = pos["cost_basis"] + (shares * price)
                total_shares = pos["shares"] + shares
                pos["avg_price"] = total_cost / total_shares if total_shares > 0 else 0
                pos["shares"] = total_shares
                pos["cost_basis"] = total_cost
            elif direction == "SELL":
                # Close position (full or partial)
                if pos["shares"] > 0:
                    # Calculate P&L for this sale
                    pnl = (price - pos["avg_price"]) * shares

                    if pnl > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1

                    # Update position
                    pos["shares"] -= shares
                    pos["cost_basis"] -= shares * pos["avg_price"]

        total_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        return win_rate, winning_trades, losing_trades

    def calculate_profit_factor(
        self,
        trades: pd.DataFrame,
    ) -> float:
        """
        Calculate profit factor (gross profit / gross loss).

        Args:
            trades: DataFrame with trade history

        Returns:
            Profit factor (>1 means profitable, <1 means unprofitable)
        """
        if trades.empty:
            return 0.0

        gross_profit = 0.0
        gross_loss = 0.0

        positions = {}

        for _, trade in trades.iterrows():
            ticker = trade["ticker"]
            direction = trade["direction"]
            price = trade["price"]
            shares = trade["shares"]

            if ticker not in positions:
                positions[ticker] = {"shares": 0, "avg_price": 0, "cost_basis": 0}

            pos = positions[ticker]

            if direction == "BUY":
                total_cost = pos["cost_basis"] + (shares * price)
                total_shares = pos["shares"] + shares
                pos["avg_price"] = total_cost / total_shares if total_shares > 0 else 0
                pos["shares"] = total_shares
                pos["cost_basis"] = total_cost
            elif direction == "SELL":
                if pos["shares"] > 0:
                    pnl = (price - pos["avg_price"]) * shares
                    if pnl > 0:
                        gross_profit += pnl
                    else:
                        gross_loss += abs(pnl)

                    pos["shares"] -= shares
                    pos["cost_basis"] -= shares * pos["avg_price"]

        if gross_loss == 0:
            return np.inf if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def calculate_cagr(
        self,
        equity_curve: pd.Series,
    ) -> float:
        """
        Calculate Compound Annual Growth Rate (CAGR).

        Args:
            equity_curve: Series of portfolio values over time

        Returns:
            CAGR as percentage

        Formula:
            CAGR = ((Ending Value / Beginning Value) ^ (1 / Years)) - 1
        """
        if len(equity_curve) < 2:
            logger.warning("Insufficient data for CAGR calculation")
            return 0.0

        start_value = equity_curve.iloc[0]
        end_value = equity_curve.iloc[-1]

        # Calculate time period in years
        time_delta = equity_curve.index[-1] - equity_curve.index[0]
        years = time_delta.days / 365.25

        if years == 0 or start_value == 0:
            return 0.0

        # Calculate CAGR
        cagr = (pow(end_value / start_value, 1 / years) - 1) * 100

        return cagr

    def calculate_volatility(
        self,
        returns: pd.Series,
        annualize: bool = True,
    ) -> float:
        """
        Calculate volatility (standard deviation of returns).

        Args:
            returns: Series of period returns
            annualize: Whether to annualize the volatility

        Returns:
            Volatility as percentage
        """
        if len(returns) < 2:
            logger.warning("Insufficient data for volatility calculation")
            return 0.0

        volatility = returns.std()

        if annualize:
            volatility = volatility * np.sqrt(self.trading_days_per_year)

        return volatility * 100

    def calculate_calmar_ratio(
        self,
        equity_curve: pd.Series,
    ) -> float:
        """
        Calculate Calmar ratio (CAGR / Max Drawdown).

        The Calmar ratio measures return relative to worst drawdown.

        Args:
            equity_curve: Series of portfolio values over time

        Returns:
            Calmar ratio
        """
        cagr = self.calculate_cagr(equity_curve)
        max_dd, _, _ = self.calculate_max_drawdown(equity_curve)

        if max_dd == 0:
            return np.inf if cagr > 0 else 0.0

        return cagr / max_dd

    def compare_to_benchmark(
        self,
        strategy_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> dict:
        """
        Compare strategy performance to benchmark.

        Args:
            strategy_returns: Strategy returns series
            benchmark_returns: Benchmark returns series

        Returns:
            Dictionary with comparison metrics

        Raises:
            DataValidationError: If series have different lengths
        """
        # Align the series
        if len(strategy_returns) != len(benchmark_returns):
            # Find common dates
            common_dates = strategy_returns.index.intersection(benchmark_returns.index)
            if len(common_dates) == 0:
                raise DataValidationError(
                    "No overlapping dates between strategy and benchmark",
                    field="dates",
                    value="no overlap",
                    expected="overlapping dates",
                )
            strategy_returns = strategy_returns.loc[common_dates]
            benchmark_returns = benchmark_returns.loc[common_dates]

        # Calculate metrics for both
        strategy_sharpe = self.calculate_sharpe_ratio(strategy_returns)
        benchmark_sharpe = self.calculate_sharpe_ratio(benchmark_returns)

        strategy_vol = self.calculate_volatility(strategy_returns)
        benchmark_vol = self.calculate_volatility(benchmark_returns)

        # Calculate cumulative returns
        strategy_cumulative = (1 + strategy_returns).prod() - 1
        benchmark_cumulative = (1 + benchmark_returns).prod() - 1

        # Calculate correlation
        correlation = strategy_returns.corr(benchmark_returns)

        # Calculate beta (volatility ratio)
        beta = strategy_returns.cov(benchmark_returns) / benchmark_returns.var()

        # Calculate alpha (excess return)
        alpha = strategy_cumulative - (beta * benchmark_cumulative)

        # Calculate tracking error
        tracking_error = (strategy_returns - benchmark_returns).std() * np.sqrt(
            self.trading_days_per_year
        )

        # Calculate information ratio
        excess_returns = strategy_returns - benchmark_returns
        information_ratio = (
            excess_returns.mean() / excess_returns.std()
            if excess_returns.std() > 0
            else 0.0
        )
        information_ratio *= np.sqrt(self.trading_days_per_year)

        return {
            "strategy_sharpe": strategy_sharpe,
            "benchmark_sharpe": benchmark_sharpe,
            "sharpe_difference": strategy_sharpe - benchmark_sharpe,
            "strategy_volatility": strategy_vol,
            "benchmark_volatility": benchmark_vol,
            "strategy_cumulative_return": strategy_cumulative * 100,
            "benchmark_cumulative_return": benchmark_cumulative * 100,
            "excess_return": (strategy_cumulative - benchmark_cumulative) * 100,
            "correlation": correlation,
            "beta": beta,
            "alpha": alpha * 100,
            "tracking_error": tracking_error * 100,
            "information_ratio": information_ratio,
        }

    def calculate_all_metrics(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        trades: pd.DataFrame,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> dict:
        """
        Calculate all performance metrics.

        Args:
            equity_curve: Portfolio value over time
            returns: Period returns
            trades: Trade history
            benchmark_returns: Optional benchmark returns for comparison

        Returns:
            Dictionary with all calculated metrics
        """
        max_dd, peak_date, trough_date = self.calculate_max_drawdown(equity_curve)
        win_rate, wins, losses = self.calculate_win_rate(trades)

        metrics = {
            # Returns
            "total_return": (
                (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100
                if len(equity_curve) > 0
                else 0.0
            ),
            "cagr": self.calculate_cagr(equity_curve),
            # Risk metrics
            "volatility": self.calculate_volatility(returns),
            "sharpe_ratio": self.calculate_sharpe_ratio(returns),
            "sortino_ratio": self.calculate_sortino_ratio(returns),
            # Drawdown
            "max_drawdown": max_dd,
            "max_drawdown_peak": peak_date,
            "max_drawdown_trough": trough_date,
            "calmar_ratio": self.calculate_calmar_ratio(equity_curve),
            # Trade statistics
            "win_rate": win_rate,
            "num_wins": wins,
            "num_losses": losses,
            "total_trades": len(trades),
            "profit_factor": self.calculate_profit_factor(trades),
        }

        # Add benchmark comparison if provided
        if benchmark_returns is not None:
            benchmark_metrics = self.compare_to_benchmark(returns, benchmark_returns)
            metrics.update({"benchmark": benchmark_metrics})

        return metrics
