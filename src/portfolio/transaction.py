"""
Transaction tracking for portfolio management.

This module provides transaction recording and management capabilities,
tracking all portfolio activity including buys, sells, and dividends.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class TransactionType(Enum):
    """
    Type of portfolio transaction.

    Attributes:
        BUY: Purchase of shares
        SELL: Sale of shares
        DIVIDEND: Dividend payment received
    """
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"

    def __str__(self) -> str:
        return self.value


@dataclass
class Transaction:
    """
    Represents a single portfolio transaction.

    Attributes:
        ticker: Stock ticker symbol (e.g., "AAPL", "1681.HK")
        transaction_type: Type of transaction (BUY, SELL, DIVIDEND)
        shares: Number of shares (N/A for dividends)
        price: Price per share (N/A for dividends)
        fees: Transaction fees (commission, exchange fees, etc.)
        date: Transaction date
        currency: Currency of transaction
        notes: Optional transaction notes
        transaction_id: Unique transaction identifier (auto-generated)
        dividend_amount: Total dividend amount (for DIVIDEND type only)

    Example:
        >>> # Record a stock purchase
        >>> buy = Transaction(
        ...     ticker="AAPL",
        ...     transaction_type=TransactionType.BUY,
        ...     shares=100,
        ...     price=150.0,
        ...     fees=5.0,
        ...     date=datetime.now(),
        ...     currency="USD",
        ...     notes="Initial purchase"
        ... )
        >>> print(buy.total_amount)
        15005.0

        >>> # Record a dividend
        >>> div = Transaction(
        ...     ticker="AAPL",
        ...     transaction_type=TransactionType.DIVIDEND,
        ...     shares=0,
        ...     price=0,
        ...     fees=0,
        ...     date=datetime.now(),
        ...     currency="USD",
        ...     dividend_amount=100.0
        ... )
    """

    ticker: str
    transaction_type: TransactionType
    shares: float
    price: float
    fees: float
    date: datetime
    currency: str
    notes: Optional[str] = None
    transaction_id: Optional[str] = None
    dividend_amount: Optional[float] = None

    def __post_init__(self):
        """Validate and normalize transaction data."""
        # Normalize ticker to uppercase
        self.ticker = self.ticker.strip().upper()

        # Normalize currency code
        self.currency = self.currency.strip().upper()

        # Convert string to enum if needed
        if isinstance(self.transaction_type, str):
            self.transaction_type = TransactionType(self.transaction_type)

        # Generate transaction ID if not provided
        if self.transaction_id is None:
            self.transaction_id = self._generate_transaction_id()

        # Validate based on transaction type
        if self.transaction_type == TransactionType.DIVIDEND:
            # Dividends don't have shares or price, but need dividend_amount
            if self.dividend_amount is None or self.dividend_amount <= 0:
                raise ValueError(
                    f"DIVIDEND transaction must have positive dividend_amount, got {self.dividend_amount}"
                )
        else:
            # BUY and SELL must have positive shares and price
            if self.shares <= 0:
                raise ValueError(f"Shares must be positive for {self.transaction_type}, got {self.shares}")
            if self.price < 0:
                raise ValueError(f"Price cannot be negative, got {self.price}")

        # Fees cannot be negative
        if self.fees < 0:
            raise ValueError(f"Fees cannot be negative, got {self.fees}")

    def _generate_transaction_id(self) -> str:
        """
        Generate a unique transaction ID.

        Format: {TICKER}_{TYPE}_{TIMESTAMP}

        Example: AAPL_BUY_20240101123045
        """
        timestamp_str = self.date.strftime("%Y%m%d%H%M%S%f")
        return f"{self.ticker}_{self.transaction_type.value}_{timestamp_str}"

    @property
    def total_amount(self) -> float:
        """
        Calculate total transaction amount.

        For BUY: (shares * price) + fees
        For SELL: (shares * price) - fees
        For DIVIDEND: dividend_amount

        Returns:
            Total transaction amount including fees
        """
        if self.transaction_type == TransactionType.DIVIDEND:
            return self.dividend_amount or 0.0
        elif self.transaction_type == TransactionType.BUY:
            return (self.shares * self.price) + self.fees
        else:  # SELL
            return (self.shares * self.price) - self.fees

    @property
    def net_proceeds(self) -> float:
        """
        Calculate net proceeds (for SELL transactions).

        Returns:
            Net amount after fees for SELL, 0 for other types
        """
        if self.transaction_type == TransactionType.SELL:
            return (self.shares * self.price) - self.fees
        return 0.0

    @property
    def cost_basis(self) -> float:
        """
        Calculate cost basis (for BUY transactions).

        Returns:
            Total cost including fees for BUY, 0 for other types
        """
        if self.transaction_type == TransactionType.BUY:
            return (self.shares * self.price) + self.fees
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert transaction to dictionary representation.

        Returns:
            Dictionary with all transaction data, suitable for JSON serialization

        Example:
            >>> transaction.to_dict()
            {'ticker': 'AAPL', 'transaction_type': 'BUY', ...}
        """
        return {
            "transaction_id": self.transaction_id,
            "ticker": self.ticker,
            "transaction_type": self.transaction_type.value,
            "shares": self.shares,
            "price": self.price,
            "fees": self.fees,
            "date": self.date.isoformat(),
            "currency": self.currency,
            "notes": self.notes,
            "dividend_amount": self.dividend_amount,
            "total_amount": self.total_amount,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """
        Create transaction from dictionary representation.

        Args:
            data: Dictionary with transaction data

        Returns:
            New Transaction instance

        Example:
            >>> data = {"ticker": "AAPL", "transaction_type": "BUY", ...}
            >>> transaction = Transaction.from_dict(data)
        """
        # Convert ISO format string back to datetime
        date = data.get("date")
        if isinstance(date, str):
            date = datetime.fromisoformat(date)

        # Convert string to enum
        transaction_type = data.get("transaction_type")
        if isinstance(transaction_type, str):
            transaction_type = TransactionType(transaction_type)

        return cls(
            transaction_id=data.get("transaction_id"),
            ticker=data["ticker"],
            transaction_type=transaction_type,
            shares=data["shares"],
            price=data["price"],
            fees=data["fees"],
            date=date,
            currency=data["currency"],
            notes=data.get("notes"),
            dividend_amount=data.get("dividend_amount"),
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        if self.transaction_type == TransactionType.DIVIDEND:
            return (
                f"Transaction(id={self.transaction_id}, ticker={self.ticker}, "
                f"type=DIVIDEND, amount={self.dividend_amount:.2f} {self.currency}, "
                f"date={self.date.date()})"
            )
        else:
            return (
                f"Transaction(id={self.transaction_id}, ticker={self.ticker}, "
                f"type={self.transaction_type.value}, shares={self.shares:.2f}, "
                f"price={self.price:.2f}, total={self.total_amount:.2f} {self.currency}, "
                f"date={self.date.date()})"
            )


def create_buy_transaction(
    ticker: str,
    shares: float,
    price: float,
    date: datetime,
    currency: str = "USD",
    fees: float = 0.0,
    notes: Optional[str] = None
) -> Transaction:
    """
    Convenience function to create a BUY transaction.

    Args:
        ticker: Stock ticker symbol
        shares: Number of shares purchased
        price: Price per share
        date: Transaction date
        currency: Currency code (default "USD")
        fees: Transaction fees (default 0.0)
        notes: Optional notes

    Returns:
        New Transaction instance

    Example:
        >>> buy = create_buy_transaction("AAPL", 100, 150.0, datetime.now())
    """
    return Transaction(
        ticker=ticker,
        transaction_type=TransactionType.BUY,
        shares=shares,
        price=price,
        fees=fees,
        date=date,
        currency=currency,
        notes=notes,
    )


def create_sell_transaction(
    ticker: str,
    shares: float,
    price: float,
    date: datetime,
    currency: str = "USD",
    fees: float = 0.0,
    notes: Optional[str] = None
) -> Transaction:
    """
    Convenience function to create a SELL transaction.

    Args:
        ticker: Stock ticker symbol
        shares: Number of shares sold
        price: Price per share
        date: Transaction date
        currency: Currency code (default "USD")
        fees: Transaction fees (default 0.0)
        notes: Optional notes

    Returns:
        New Transaction instance

    Example:
        >>> sell = create_sell_transaction("AAPL", 50, 175.0, datetime.now())
    """
    return Transaction(
        ticker=ticker,
        transaction_type=TransactionType.SELL,
        shares=shares,
        price=price,
        fees=fees,
        date=date,
        currency=currency,
        notes=notes,
    )


def create_dividend_transaction(
    ticker: str,
    dividend_amount: float,
    date: datetime,
    currency: str = "USD",
    notes: Optional[str] = None
) -> Transaction:
    """
    Convenience function to create a DIVIDEND transaction.

    Args:
        ticker: Stock ticker symbol
        dividend_amount: Total dividend amount received
        date: Transaction date
        currency: Currency code (default "USD")
        notes: Optional notes

    Returns:
        New Transaction instance

    Example:
        >>> div = create_dividend_transaction("AAPL", 100.0, datetime.now())
    """
    return Transaction(
        ticker=ticker,
        transaction_type=TransactionType.DIVIDEND,
        shares=0,
        price=0,
        fees=0,
        date=date,
        currency=currency,
        dividend_amount=dividend_amount,
        notes=notes,
    )
