"""
Portfolio manager for tracking positions and transactions.

This module provides the central PortfolioManager class for managing
a collection of positions, recording transactions, and calculating
portfolio-level metrics with multi-currency support.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import structlog

from .position import Position
from .transaction import Transaction, TransactionType
from ..exceptions import InvestmentAgentError

logger = structlog.get_logger(__name__)


class PortfolioError(InvestmentAgentError):
    """Base exception for portfolio-related errors."""
    pass


class PositionNotFoundError(PortfolioError):
    """Raised when a position is not found in the portfolio."""
    pass


class InsufficientSharesError(PortfolioError):
    """Raised when trying to sell more shares than available."""
    pass


class PortfolioManager:
    """
    Manages a collection of positions and tracks all transactions.

    The PortfolioManager provides a complete portfolio management system with:
    - Position tracking with real-time P&L
    - Transaction history
    - Multi-currency support
    - Portfolio-level metrics and aggregations

    Example:
        >>> manager = PortfolioManager(name="My Portfolio")
        >>> # Add a position
        >>> position = Position("AAPL", 100, 150.0, "USD", datetime.now())
        >>> manager.add_position(position)
        >>> # Record a transaction
        >>> transaction = create_buy_transaction("AAPL", 50, 155.0, datetime.now())
        >>> manager.record_transaction(transaction)
        >>> # Get portfolio metrics
        >>> total_value = manager.get_total_value()
        >>> total_pnl = manager.get_total_pnl()
    """

    def __init__(self, name: str = "Portfolio", base_currency: str = "USD"):
        """
        Initialize portfolio manager.

        Args:
            name: Portfolio name
            base_currency: Base currency for portfolio reporting (default "USD")
        """
        self.name = name
        self.base_currency = base_currency.strip().upper()
        self._positions: Dict[str, Position] = {}
        self._transactions: List[Transaction] = []
        self._created_at = datetime.now()

        logger.info(
            "portfolio_manager_initialized",
            name=self.name,
            base_currency=self.base_currency
        )

    @property
    def positions(self) -> Dict[str, Position]:
        """Get all positions (read-only view)."""
        return self._positions.copy()

    @property
    def transactions(self) -> List[Transaction]:
        """Get all transactions (read-only view)."""
        return self._transactions.copy()

    def add_position(self, position: Position) -> None:
        """
        Add a new position to the portfolio.

        Args:
            position: Position to add

        Raises:
            PortfolioError: If position with same ticker already exists

        Example:
            >>> position = Position("AAPL", 100, 150.0, "USD", datetime.now())
            >>> manager.add_position(position)
        """
        ticker = position.ticker.upper()

        if ticker in self._positions:
            raise PortfolioError(
                f"Position for {ticker} already exists. Use update_position() or record a transaction instead.",
                details={"ticker": ticker}
            )

        self._positions[ticker] = position

        logger.info(
            "position_added",
            ticker=ticker,
            shares=position.shares,
            avg_cost=position.avg_cost,
            currency=position.currency
        )

    def remove_position(self, ticker: str) -> Position:
        """
        Remove a position from the portfolio.

        Args:
            ticker: Ticker symbol of position to remove

        Returns:
            The removed position

        Raises:
            PositionNotFoundError: If position doesn't exist

        Example:
            >>> removed = manager.remove_position("AAPL")
        """
        ticker = ticker.strip().upper()

        if ticker not in self._positions:
            raise PositionNotFoundError(
                f"No position found for {ticker}",
                details={"ticker": ticker}
            )

        position = self._positions.pop(ticker)

        logger.info(
            "position_removed",
            ticker=ticker,
            shares=position.shares,
            value=position.current_value
        )

        return position

    def get_position(self, ticker: str) -> Optional[Position]:
        """
        Get a position by ticker.

        Args:
            ticker: Ticker symbol

        Returns:
            Position if found, None otherwise

        Example:
            >>> position = manager.get_position("AAPL")
        """
        return self._positions.get(ticker.strip().upper())

    def has_position(self, ticker: str) -> bool:
        """
        Check if portfolio contains a position.

        Args:
            ticker: Ticker symbol

        Returns:
            True if position exists, False otherwise
        """
        return ticker.strip().upper() in self._positions

    def update_position_price(self, ticker: str, price: float, timestamp: Optional[datetime] = None) -> None:
        """
        Update the current price for a position.

        Args:
            ticker: Ticker symbol
            price: New market price
            timestamp: Time of price update (defaults to now)

        Raises:
            PositionNotFoundError: If position doesn't exist

        Example:
            >>> manager.update_position_price("AAPL", 175.0)
        """
        position = self.get_position(ticker)
        if position is None:
            raise PositionNotFoundError(
                f"No position found for {ticker}",
                details={"ticker": ticker}
            )

        position.update_price(price, timestamp)

        logger.debug(
            "position_price_updated",
            ticker=ticker,
            price=price,
            value=position.current_value,
            pnl=position.unrealized_pnl
        )

    def record_transaction(self, transaction: Transaction) -> None:
        """
        Record a transaction and update positions accordingly.

        For BUY: Creates position if new, or adds shares to existing position
        For SELL: Reduces shares in existing position
        For DIVIDEND: Records dividend but doesn't change position

        Args:
            transaction: Transaction to record

        Raises:
            PositionNotFoundError: For SELL when position doesn't exist
            InsufficientSharesError: For SELL when insufficient shares

        Example:
            >>> buy = create_buy_transaction("AAPL", 100, 150.0, datetime.now())
            >>> manager.record_transaction(buy)
        """
        ticker = transaction.ticker.upper()

        # Add transaction to history
        self._transactions.append(transaction)

        # Process based on transaction type
        if transaction.transaction_type == TransactionType.BUY:
            self._process_buy(transaction)
        elif transaction.transaction_type == TransactionType.SELL:
            self._process_sell(transaction)
        elif transaction.transaction_type == TransactionType.DIVIDEND:
            self._process_dividend(transaction)

        logger.info(
            "transaction_recorded",
            transaction_id=transaction.transaction_id,
            ticker=ticker,
            type=transaction.transaction_type.value,
            amount=transaction.total_amount
        )

    def _process_buy(self, transaction: Transaction) -> None:
        """Process a BUY transaction."""
        ticker = transaction.ticker.upper()

        if ticker in self._positions:
            # Add to existing position
            position = self._positions[ticker]

            # Check currency matches
            if position.currency != transaction.currency:
                logger.warning(
                    "currency_mismatch",
                    ticker=ticker,
                    position_currency=position.currency,
                    transaction_currency=transaction.currency
                )

            # Calculate cost per share including fees
            cost_per_share = (transaction.shares * transaction.price + transaction.fees) / transaction.shares
            position.add_shares(transaction.shares, cost_per_share)
        else:
            # Create new position
            cost_per_share = (transaction.shares * transaction.price + transaction.fees) / transaction.shares
            position = Position(
                ticker=ticker,
                shares=transaction.shares,
                avg_cost=cost_per_share,
                currency=transaction.currency,
                purchase_date=transaction.date,
                notes=transaction.notes
            )
            self._positions[ticker] = position

    def _process_sell(self, transaction: Transaction) -> None:
        """Process a SELL transaction."""
        ticker = transaction.ticker.upper()

        if ticker not in self._positions:
            raise PositionNotFoundError(
                f"Cannot sell {ticker}: No position found",
                details={"ticker": ticker}
            )

        position = self._positions[ticker]

        # Check if we have enough shares
        if transaction.shares > position.shares:
            raise InsufficientSharesError(
                f"Cannot sell {transaction.shares} shares of {ticker}: only {position.shares} available",
                details={
                    "ticker": ticker,
                    "shares_to_sell": transaction.shares,
                    "shares_available": position.shares
                }
            )

        # Remove shares from position
        position.remove_shares(transaction.shares)

        # If position is now empty, remove it
        if position.shares == 0:
            del self._positions[ticker]
            logger.info("position_closed", ticker=ticker)

    def _process_dividend(self, transaction: Transaction) -> None:
        """Process a DIVIDEND transaction."""
        # Dividends are just recorded in transaction history
        # They don't affect position shares or cost basis
        logger.debug(
            "dividend_recorded",
            ticker=transaction.ticker,
            amount=transaction.dividend_amount,
            currency=transaction.currency
        )

    def get_transactions(
        self,
        ticker: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """
        Get filtered transaction history.

        Args:
            ticker: Filter by ticker (optional)
            transaction_type: Filter by type (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)

        Returns:
            List of matching transactions

        Example:
            >>> # Get all AAPL transactions
            >>> transactions = manager.get_transactions(ticker="AAPL")
            >>> # Get all buys in 2024
            >>> buys = manager.get_transactions(
            ...     transaction_type=TransactionType.BUY,
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 12, 31)
            ... )
        """
        filtered = self._transactions

        if ticker:
            ticker = ticker.strip().upper()
            filtered = [t for t in filtered if t.ticker == ticker]

        if transaction_type:
            filtered = [t for t in filtered if t.transaction_type == transaction_type]

        if start_date:
            filtered = [t for t in filtered if t.date >= start_date]

        if end_date:
            filtered = [t for t in filtered if t.date <= end_date]

        return filtered

    def get_total_value(self, currency: Optional[str] = None) -> float:
        """
        Calculate total portfolio value.

        Note: This returns the sum in mixed currencies. For proper currency
        conversion, use get_total_value_normalized() with an FX rate provider.

        Args:
            currency: Filter by currency (optional)

        Returns:
            Total current value of all positions

        Example:
            >>> total = manager.get_total_value()
            >>> usd_total = manager.get_total_value(currency="USD")
        """
        total = 0.0

        for position in self._positions.values():
            # Filter by currency if specified
            if currency and position.currency != currency.upper():
                continue

            if position.current_value is not None:
                total += position.current_value

        return total

    def get_total_cost(self, currency: Optional[str] = None) -> float:
        """
        Calculate total cost basis of portfolio.

        Args:
            currency: Filter by currency (optional)

        Returns:
            Total cost basis of all positions

        Example:
            >>> cost = manager.get_total_cost()
        """
        total = 0.0

        for position in self._positions.values():
            # Filter by currency if specified
            if currency and position.currency != currency.upper():
                continue

            total += position.total_cost

        return total

    def get_total_pnl(self, currency: Optional[str] = None) -> Tuple[float, float]:
        """
        Calculate total unrealized P&L.

        Args:
            currency: Filter by currency (optional)

        Returns:
            Tuple of (total_pnl, total_pnl_pct)

        Example:
            >>> pnl, pnl_pct = manager.get_total_pnl()
            >>> print(f"P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
        """
        total_pnl = 0.0
        total_cost = 0.0
        total_value = 0.0

        for position in self._positions.values():
            # Filter by currency if specified
            if currency and position.currency != currency.upper():
                continue

            if position.unrealized_pnl is not None:
                total_pnl += position.unrealized_pnl
                total_cost += position.total_cost
                total_value += position.current_value

        # Calculate percentage
        pnl_pct = (total_pnl / total_cost * 100.0) if total_cost > 0 else 0.0

        return total_pnl, pnl_pct

    def get_positions_by_currency(self) -> Dict[str, List[Position]]:
        """
        Group positions by currency.

        Returns:
            Dictionary mapping currency code to list of positions

        Example:
            >>> by_currency = manager.get_positions_by_currency()
            >>> usd_positions = by_currency.get("USD", [])
        """
        grouped: Dict[str, List[Position]] = defaultdict(list)

        for position in self._positions.values():
            grouped[position.currency].append(position)

        return dict(grouped)

    def get_positions_summary(self) -> Dict[str, any]:
        """
        Get a summary of all positions.

        Returns:
            Dictionary with portfolio statistics

        Example:
            >>> summary = manager.get_positions_summary()
            >>> print(summary['total_positions'])
            5
        """
        total_value = self.get_total_value()
        total_cost = self.get_total_cost()
        total_pnl, total_pnl_pct = self.get_total_pnl()

        positions_by_currency = self.get_positions_by_currency()
        currency_summary = {}
        for currency, positions in positions_by_currency.items():
            currency_value = sum(p.current_value or 0 for p in positions)
            currency_cost = sum(p.total_cost for p in positions)
            currency_pnl = currency_value - currency_cost
            currency_pnl_pct = (currency_pnl / currency_cost * 100.0) if currency_cost > 0 else 0.0

            currency_summary[currency] = {
                "positions": len(positions),
                "value": currency_value,
                "cost": currency_cost,
                "pnl": currency_pnl,
                "pnl_pct": currency_pnl_pct
            }

        return {
            "portfolio_name": self.name,
            "base_currency": self.base_currency,
            "total_positions": len(self._positions),
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "by_currency": currency_summary,
            "total_transactions": len(self._transactions),
            "created_at": self._created_at.isoformat()
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        total_value = self.get_total_value()
        total_pnl, total_pnl_pct = self.get_total_pnl()

        return (
            f"PortfolioManager(name={self.name}, positions={len(self._positions)}, "
            f"value={total_value:.2f}, pnl={total_pnl:+.2f} ({total_pnl_pct:+.2f}%))"
        )
