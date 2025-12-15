"""
Position tracking for portfolio management.

This module provides the Position dataclass for tracking individual stock positions
with real-time pricing, P&L calculation, and currency support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Position:
    """
    Represents a single stock position in the portfolio.

    Attributes:
        ticker: Stock ticker symbol (e.g., "AAPL", "1681.HK")
        shares: Number of shares held (can be fractional)
        avg_cost: Average cost per share in the position's currency
        currency: Currency code (e.g., "USD", "HKD", "JPY")
        purchase_date: Date when position was first established
        current_price: Most recent market price per share
        current_value: Total market value (shares * current_price)
        unrealized_pnl: Unrealized profit/loss (current_value - total_cost)
        unrealized_pnl_pct: Unrealized P&L as percentage of cost basis
        last_updated: Timestamp of last price update
        notes: Optional notes about the position

    Example:
        >>> position = Position(
        ...     ticker="AAPL",
        ...     shares=100,
        ...     avg_cost=150.0,
        ...     currency="USD",
        ...     purchase_date=datetime(2024, 1, 1)
        ... )
        >>> position.update_price(175.0)
        >>> print(f"P&L: ${position.unrealized_pnl:.2f} ({position.unrealized_pnl_pct:.2f}%)")
        P&L: $2500.00 (16.67%)
    """

    ticker: str
    shares: float
    avg_cost: float
    currency: str
    purchase_date: datetime
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    last_updated: Optional[datetime] = None
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate and normalize position data."""
        # Normalize ticker to uppercase
        self.ticker = self.ticker.strip().upper()

        # Validate shares
        if self.shares <= 0:
            raise ValueError(f"Shares must be positive, got {self.shares}")

        # Validate avg_cost
        if self.avg_cost <= 0:
            raise ValueError(f"Average cost must be positive, got {self.avg_cost}")

        # Normalize currency code
        self.currency = self.currency.strip().upper()

        # If current_price is set, calculate derived values
        if self.current_price is not None:
            self._calculate_values()

    def _calculate_values(self) -> None:
        """Calculate derived values based on current price."""
        if self.current_price is None:
            self.current_value = None
            self.unrealized_pnl = None
            self.unrealized_pnl_pct = None
            return

        # Validate current price
        if self.current_price < 0:
            logger.warning(
                "invalid_current_price",
                ticker=self.ticker,
                price=self.current_price,
                msg="Current price cannot be negative, skipping calculation"
            )
            return

        # Calculate current market value
        self.current_value = self.shares * self.current_price

        # Calculate cost basis
        total_cost = self.shares * self.avg_cost

        # Calculate unrealized P&L
        self.unrealized_pnl = self.current_value - total_cost

        # Calculate unrealized P&L percentage
        if total_cost > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / total_cost) * 100.0
        else:
            self.unrealized_pnl_pct = 0.0

    def update_price(self, price: float, timestamp: Optional[datetime] = None) -> None:
        """
        Update the current price and recalculate derived values.

        Args:
            price: New market price per share
            timestamp: Time of price update (defaults to now)

        Raises:
            ValueError: If price is negative

        Example:
            >>> position.update_price(175.0)
            >>> print(position.current_value)
            17500.0
        """
        if price < 0:
            raise ValueError(f"Price cannot be negative, got {price}")

        self.current_price = price
        self.last_updated = timestamp or datetime.now()
        self._calculate_values()

        logger.debug(
            "position_price_updated",
            ticker=self.ticker,
            price=price,
            current_value=self.current_value,
            unrealized_pnl=self.unrealized_pnl,
            unrealized_pnl_pct=self.unrealized_pnl_pct
        )

    def add_shares(self, shares: float, cost: float) -> None:
        """
        Add shares to position and recalculate average cost.

        Uses weighted average to calculate new avg_cost.

        Args:
            shares: Number of shares to add
            cost: Cost per share of new shares

        Raises:
            ValueError: If shares or cost is negative

        Example:
            >>> position = Position("AAPL", 100, 150.0, "USD", datetime.now())
            >>> position.add_shares(50, 160.0)
            >>> print(position.shares, position.avg_cost)
            150 153.33
        """
        if shares <= 0:
            raise ValueError(f"Shares to add must be positive, got {shares}")
        if cost < 0:
            raise ValueError(f"Cost cannot be negative, got {cost}")

        # Calculate new weighted average cost
        old_total_cost = self.shares * self.avg_cost
        new_total_cost = shares * cost
        total_shares = self.shares + shares

        self.avg_cost = (old_total_cost + new_total_cost) / total_shares
        self.shares = total_shares

        # Recalculate values if we have a current price
        if self.current_price is not None:
            self._calculate_values()

        logger.info(
            "shares_added",
            ticker=self.ticker,
            shares_added=shares,
            new_total_shares=self.shares,
            new_avg_cost=self.avg_cost
        )

    def remove_shares(self, shares: float) -> float:
        """
        Remove shares from position (e.g., for a sale).

        Does not change avg_cost (maintains cost basis for remaining shares).

        Args:
            shares: Number of shares to remove

        Returns:
            Average cost per share for the removed shares

        Raises:
            ValueError: If trying to remove more shares than held

        Example:
            >>> position = Position("AAPL", 100, 150.0, "USD", datetime.now())
            >>> cost = position.remove_shares(30)
            >>> print(position.shares, cost)
            70 150.0
        """
        if shares <= 0:
            raise ValueError(f"Shares to remove must be positive, got {shares}")
        if shares > self.shares:
            raise ValueError(
                f"Cannot remove {shares} shares, only {self.shares} available"
            )

        self.shares -= shares

        # Recalculate values if we have a current price
        if self.current_price is not None:
            self._calculate_values()

        logger.info(
            "shares_removed",
            ticker=self.ticker,
            shares_removed=shares,
            remaining_shares=self.shares
        )

        return self.avg_cost

    @property
    def total_cost(self) -> float:
        """Calculate total cost basis of position."""
        return self.shares * self.avg_cost

    @property
    def is_profitable(self) -> bool:
        """Check if position has unrealized gains."""
        return self.unrealized_pnl is not None and self.unrealized_pnl > 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert position to dictionary representation.

        Returns:
            Dictionary with all position data, suitable for JSON serialization

        Example:
            >>> position = Position("AAPL", 100, 150.0, "USD", datetime.now())
            >>> data = position.to_dict()
            >>> print(data['ticker'])
            AAPL
        """
        return {
            "ticker": self.ticker,
            "shares": self.shares,
            "avg_cost": self.avg_cost,
            "currency": self.currency,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "current_price": self.current_price,
            "current_value": self.current_value,
            "total_cost": self.total_cost,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        """
        Create position from dictionary representation.

        Args:
            data: Dictionary with position data

        Returns:
            New Position instance

        Example:
            >>> data = {"ticker": "AAPL", "shares": 100, "avg_cost": 150.0,
            ...         "currency": "USD", "purchase_date": "2024-01-01T00:00:00"}
            >>> position = Position.from_dict(data)
            >>> print(position.ticker)
            AAPL
        """
        # Convert ISO format strings back to datetime
        purchase_date = data.get("purchase_date")
        if isinstance(purchase_date, str):
            purchase_date = datetime.fromisoformat(purchase_date)

        last_updated = data.get("last_updated")
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)

        return cls(
            ticker=data["ticker"],
            shares=data["shares"],
            avg_cost=data["avg_cost"],
            currency=data["currency"],
            purchase_date=purchase_date,
            current_price=data.get("current_price"),
            last_updated=last_updated,
            notes=data.get("notes"),
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        pnl_str = ""
        if self.unrealized_pnl is not None and self.unrealized_pnl_pct is not None:
            pnl_str = f" | P&L: {self.unrealized_pnl:+.2f} ({self.unrealized_pnl_pct:+.2f}%)"

        return (
            f"Position(ticker={self.ticker}, shares={self.shares:.2f}, "
            f"avg_cost={self.avg_cost:.2f} {self.currency}, "
            f"value={self.current_value or 'N/A'}{pnl_str})"
        )
