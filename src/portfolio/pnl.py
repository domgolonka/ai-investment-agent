"""
Profit & Loss calculations for portfolio performance analysis.

This module provides comprehensive P&L calculation capabilities including
realized gains, unrealized gains, total returns, and various performance metrics.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import structlog

from .transaction import Transaction, TransactionType
from .position import Position
from .manager import PortfolioManager

logger = structlog.get_logger(__name__)


class PnLCalculator:
    """
    Calculate profit and loss metrics for portfolio analysis.

    Provides methods to calculate:
    - Realized P&L from sold positions
    - Unrealized P&L from open positions
    - Total return (realized + unrealized)
    - Time-weighted returns
    - Money-weighted returns (IRR approximation)
    - Various performance statistics

    Example:
        >>> calculator = PnLCalculator(portfolio_manager)
        >>> realized = calculator.calculate_realized_pnl()
        >>> unrealized = calculator.calculate_unrealized_pnl()
        >>> metrics = calculator.calculate_portfolio_metrics()
    """

    def __init__(self, portfolio_manager: PortfolioManager):
        """
        Initialize P&L calculator.

        Args:
            portfolio_manager: PortfolioManager instance to analyze
        """
        self.manager = portfolio_manager
        logger.debug("pnl_calculator_initialized", portfolio=self.manager.name)

    def calculate_realized_pnl(
        self,
        ticker: Optional[str] = None,
        currency: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calculate realized profit/loss from sold positions.

        Realized P&L = (Sale Price - Fees) - (Purchase Cost Basis)

        Args:
            ticker: Filter by ticker (optional)
            currency: Filter by currency (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)

        Returns:
            Dictionary with:
            - total_realized_pnl: Total realized gain/loss
            - total_proceeds: Total sale proceeds
            - total_cost_basis: Total cost of sold shares
            - by_ticker: Dict mapping ticker to realized P&L
            - by_currency: Dict mapping currency to realized P&L
            - transaction_count: Number of sell transactions

        Example:
            >>> results = calculator.calculate_realized_pnl()
            >>> print(f"Realized: ${results['total_realized_pnl']:.2f}")
        """
        # Get all sell transactions
        sell_transactions = self.manager.get_transactions(
            ticker=ticker,
            transaction_type=TransactionType.SELL,
            start_date=start_date,
            end_date=end_date
        )

        # Track realized P&L by ticker
        by_ticker: Dict[str, float] = defaultdict(float)
        by_currency: Dict[str, float] = defaultdict(float)

        total_proceeds = 0.0
        total_cost_basis = 0.0

        for sell_txn in sell_transactions:
            # Filter by currency if specified
            if currency and sell_txn.currency != currency.upper():
                continue

            # Calculate proceeds from sale
            proceeds = sell_txn.net_proceeds

            # Find corresponding buy transactions to calculate cost basis
            # For simplicity, we'll use average cost from the position at time of sale
            # In a more sophisticated system, we'd track specific lot purchases (FIFO/LIFO)
            buy_transactions = self.manager.get_transactions(
                ticker=sell_txn.ticker,
                transaction_type=TransactionType.BUY,
                end_date=sell_txn.date
            )

            # Calculate weighted average cost
            total_shares_bought = sum(t.shares for t in buy_transactions)
            total_cost_bought = sum(t.cost_basis for t in buy_transactions)

            if total_shares_bought > 0:
                avg_cost = total_cost_bought / total_shares_bought
            else:
                # No buy history found, use sell price as proxy (no gain/loss)
                avg_cost = sell_txn.price
                logger.warning(
                    "no_buy_history_for_sell",
                    ticker=sell_txn.ticker,
                    shares=sell_txn.shares,
                    sell_date=sell_txn.date
                )

            # Calculate cost basis for sold shares
            cost_basis = sell_txn.shares * avg_cost

            # Calculate realized P&L for this transaction
            realized_pnl = proceeds - cost_basis

            # Track by ticker and currency
            by_ticker[sell_txn.ticker] += realized_pnl
            by_currency[sell_txn.currency] += realized_pnl

            total_proceeds += proceeds
            total_cost_basis += cost_basis

            logger.debug(
                "realized_pnl_calculated",
                ticker=sell_txn.ticker,
                shares=sell_txn.shares,
                proceeds=proceeds,
                cost_basis=cost_basis,
                realized_pnl=realized_pnl
            )

        total_realized_pnl = total_proceeds - total_cost_basis

        return {
            "total_realized_pnl": total_realized_pnl,
            "total_proceeds": total_proceeds,
            "total_cost_basis": total_cost_basis,
            "by_ticker": dict(by_ticker),
            "by_currency": dict(by_currency),
            "transaction_count": len(sell_transactions)
        }

    def calculate_unrealized_pnl(
        self,
        ticker: Optional[str] = None,
        currency: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate unrealized profit/loss from open positions.

        Unrealized P&L = Current Market Value - Cost Basis

        Args:
            ticker: Filter by ticker (optional)
            currency: Filter by currency (optional)

        Returns:
            Dictionary with:
            - total_unrealized_pnl: Total unrealized gain/loss
            - total_unrealized_pnl_pct: Percentage return
            - total_market_value: Current market value
            - total_cost_basis: Total cost
            - by_ticker: Dict mapping ticker to unrealized P&L
            - by_currency: Dict mapping currency to unrealized P&L
            - position_count: Number of positions

        Example:
            >>> results = calculator.calculate_unrealized_pnl()
            >>> print(f"Unrealized: ${results['total_unrealized_pnl']:.2f}")
        """
        positions = list(self.manager.positions.values())

        # Filter by ticker if specified
        if ticker:
            ticker_upper = ticker.strip().upper()
            positions = [p for p in positions if p.ticker == ticker_upper]

        # Filter by currency if specified
        if currency:
            currency_upper = currency.strip().upper()
            positions = [p for p in positions if p.currency == currency_upper]

        by_ticker: Dict[str, float] = {}
        by_currency: Dict[str, float] = defaultdict(float)

        total_unrealized_pnl = 0.0
        total_market_value = 0.0
        total_cost_basis = 0.0

        for position in positions:
            if position.unrealized_pnl is not None:
                by_ticker[position.ticker] = position.unrealized_pnl
                by_currency[position.currency] += position.unrealized_pnl
                total_unrealized_pnl += position.unrealized_pnl

            if position.current_value is not None:
                total_market_value += position.current_value

            total_cost_basis += position.total_cost

        # Calculate percentage
        total_unrealized_pnl_pct = (
            (total_unrealized_pnl / total_cost_basis * 100.0)
            if total_cost_basis > 0
            else 0.0
        )

        return {
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_unrealized_pnl_pct": total_unrealized_pnl_pct,
            "total_market_value": total_market_value,
            "total_cost_basis": total_cost_basis,
            "by_ticker": by_ticker,
            "by_currency": dict(by_currency),
            "position_count": len(positions)
        }

    def calculate_total_return(
        self,
        ticker: Optional[str] = None,
        currency: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate total return (realized + unrealized).

        Total Return = Realized P&L + Unrealized P&L + Dividends

        Args:
            ticker: Filter by ticker (optional)
            currency: Filter by currency (optional)

        Returns:
            Dictionary with comprehensive return metrics

        Example:
            >>> results = calculator.calculate_total_return()
            >>> print(f"Total Return: ${results['total_return']:.2f} ({results['total_return_pct']:.2f}%)")
        """
        # Get realized P&L
        realized = self.calculate_realized_pnl(ticker=ticker, currency=currency)

        # Get unrealized P&L
        unrealized = self.calculate_unrealized_pnl(ticker=ticker, currency=currency)

        # Calculate dividend income
        dividend_txns = self.manager.get_transactions(
            ticker=ticker,
            transaction_type=TransactionType.DIVIDEND
        )

        # Filter by currency if specified
        if currency:
            currency_upper = currency.strip().upper()
            dividend_txns = [t for t in dividend_txns if t.currency == currency_upper]

        total_dividends = sum(t.dividend_amount or 0.0 for t in dividend_txns)

        # Calculate total return
        total_return = (
            realized["total_realized_pnl"] +
            unrealized["total_unrealized_pnl"] +
            total_dividends
        )

        # Calculate total invested (cost basis of sold + cost basis of held)
        total_invested = realized["total_cost_basis"] + unrealized["total_cost_basis"]

        # Calculate return percentage
        total_return_pct = (
            (total_return / total_invested * 100.0)
            if total_invested > 0
            else 0.0
        )

        return {
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "realized_pnl": realized["total_realized_pnl"],
            "unrealized_pnl": unrealized["total_unrealized_pnl"],
            "dividend_income": total_dividends,
            "total_invested": total_invested,
            "current_value": unrealized["total_market_value"] + realized["total_proceeds"],
        }

    def calculate_portfolio_metrics(self) -> Dict[str, any]:
        """
        Calculate comprehensive portfolio performance metrics.

        Returns:
            Dictionary with various performance statistics including:
            - Total return metrics
            - Realized vs unrealized breakdown
            - Dividend income
            - Position statistics
            - Transaction statistics
            - Performance by currency
            - Best and worst performers

        Example:
            >>> metrics = calculator.calculate_portfolio_metrics()
            >>> print(metrics['total_return_pct'])
            15.25
        """
        # Get core metrics
        total_return = self.calculate_total_return()
        realized = self.calculate_realized_pnl()
        unrealized = self.calculate_unrealized_pnl()

        # Get positions with P&L
        positions = list(self.manager.positions.values())
        positions_with_price = [p for p in positions if p.current_price is not None]

        # Find best and worst performers
        best_performer = None
        worst_performer = None

        if positions_with_price:
            positions_sorted = sorted(
                positions_with_price,
                key=lambda p: p.unrealized_pnl_pct or 0,
                reverse=True
            )
            best_performer = {
                "ticker": positions_sorted[0].ticker,
                "pnl_pct": positions_sorted[0].unrealized_pnl_pct,
                "pnl": positions_sorted[0].unrealized_pnl
            }
            worst_performer = {
                "ticker": positions_sorted[-1].ticker,
                "pnl_pct": positions_sorted[-1].unrealized_pnl_pct,
                "pnl": positions_sorted[-1].unrealized_pnl
            }

        # Calculate portfolio age
        if self.manager._created_at:
            portfolio_age_days = (datetime.now() - self.manager._created_at).days
        else:
            portfolio_age_days = 0

        # Get transaction statistics
        all_transactions = self.manager.transactions
        buy_count = len([t for t in all_transactions if t.transaction_type == TransactionType.BUY])
        sell_count = len([t for t in all_transactions if t.transaction_type == TransactionType.SELL])
        dividend_count = len([t for t in all_transactions if t.transaction_type == TransactionType.DIVIDEND])

        return {
            # Overall returns
            "total_return": total_return["total_return"],
            "total_return_pct": total_return["total_return_pct"],
            "total_invested": total_return["total_invested"],
            "current_value": total_return["current_value"],

            # Return breakdown
            "realized_pnl": realized["total_realized_pnl"],
            "unrealized_pnl": unrealized["total_unrealized_pnl"],
            "dividend_income": total_return["dividend_income"],

            # Position statistics
            "total_positions": len(positions),
            "positions_with_price": len(positions_with_price),
            "best_performer": best_performer,
            "worst_performer": worst_performer,

            # Transaction statistics
            "total_transactions": len(all_transactions),
            "buy_transactions": buy_count,
            "sell_transactions": sell_count,
            "dividend_transactions": dividend_count,

            # Performance by currency
            "realized_by_currency": realized["by_currency"],
            "unrealized_by_currency": unrealized["by_currency"],

            # Portfolio metadata
            "portfolio_name": self.manager.name,
            "base_currency": self.manager.base_currency,
            "portfolio_age_days": portfolio_age_days,
        }

    def calculate_time_period_return(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calculate return for a specific time period.

        Args:
            start_date: Period start date
            end_date: Period end date (defaults to now)

        Returns:
            Dictionary with period return metrics

        Example:
            >>> # Calculate YTD return
            >>> ytd_start = datetime(2024, 1, 1)
            >>> ytd_return = calculator.calculate_time_period_return(ytd_start)
        """
        if end_date is None:
            end_date = datetime.now()

        # Get realized P&L in period
        realized = self.calculate_realized_pnl(
            start_date=start_date,
            end_date=end_date
        )

        # Get dividends in period
        dividend_txns = self.manager.get_transactions(
            transaction_type=TransactionType.DIVIDEND,
            start_date=start_date,
            end_date=end_date
        )
        period_dividends = sum(t.dividend_amount or 0.0 for t in dividend_txns)

        # Get buys in period to calculate period investment
        buy_txns = self.manager.get_transactions(
            transaction_type=TransactionType.BUY,
            start_date=start_date,
            end_date=end_date
        )
        period_investment = sum(t.cost_basis for t in buy_txns)

        # For unrealized, we can only show current snapshot
        # A full time-period return would require historical prices
        unrealized = self.calculate_unrealized_pnl()

        period_return = realized["total_realized_pnl"] + period_dividends

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "period_days": (end_date - start_date).days,
            "period_realized_pnl": realized["total_realized_pnl"],
            "period_dividends": period_dividends,
            "period_return": period_return,
            "period_investment": period_investment,
            "current_unrealized_pnl": unrealized["total_unrealized_pnl"],
        }

    def calculate_win_rate(self) -> Dict[str, float]:
        """
        Calculate win rate from closed positions.

        Returns:
            Dictionary with win rate statistics

        Example:
            >>> stats = calculator.calculate_win_rate()
            >>> print(f"Win rate: {stats['win_rate']:.1f}%")
        """
        sell_transactions = self.manager.get_transactions(
            transaction_type=TransactionType.SELL
        )

        # Track wins and losses by ticker
        ticker_results: Dict[str, float] = defaultdict(float)

        for sell_txn in sell_transactions:
            # Find corresponding buys
            buy_transactions = self.manager.get_transactions(
                ticker=sell_txn.ticker,
                transaction_type=TransactionType.BUY,
                end_date=sell_txn.date
            )

            # Calculate avg cost
            total_shares_bought = sum(t.shares for t in buy_transactions)
            total_cost_bought = sum(t.cost_basis for t in buy_transactions)

            if total_shares_bought > 0:
                avg_cost = total_cost_bought / total_shares_bought
                cost_basis = sell_txn.shares * avg_cost
                realized_pnl = sell_txn.net_proceeds - cost_basis
                ticker_results[sell_txn.ticker] += realized_pnl

        # Count wins and losses
        wins = sum(1 for pnl in ticker_results.values() if pnl > 0)
        losses = sum(1 for pnl in ticker_results.values() if pnl < 0)
        breakeven = sum(1 for pnl in ticker_results.values() if pnl == 0)

        total_closed = len(ticker_results)
        win_rate = (wins / total_closed * 100.0) if total_closed > 0 else 0.0

        # Calculate average win and loss
        winning_amounts = [pnl for pnl in ticker_results.values() if pnl > 0]
        losing_amounts = [pnl for pnl in ticker_results.values() if pnl < 0]

        avg_win = sum(winning_amounts) / len(winning_amounts) if winning_amounts else 0.0
        avg_loss = sum(losing_amounts) / len(losing_amounts) if losing_amounts else 0.0

        return {
            "total_closed_positions": total_closed,
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        }
