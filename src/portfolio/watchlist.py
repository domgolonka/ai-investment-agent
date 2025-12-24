"""
Watchlist model for tracking stocks of interest.

This module provides the WatchlistItem dataclass for tracking stocks
before they are purchased and converted into portfolio positions.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class WatchlistItem:
    """
    Represents a stock being watched before purchase.

    Watchlist items are created from analyzed stocks and can later be
    converted to actual portfolio positions when the user decides to buy.

    Attributes:
        ticker: Stock ticker symbol
        company_name: Full company name
        portfolio_name: Name of the portfolio this watchlist belongs to
        analysis_id: Reference to the analysis_history record
        target_price: Price the user is willing to buy at
        notes: User notes about why this stock is watched
        added_at: When the stock was added to watchlist
        id: Database ID (set after save)

        # Populated when loaded with analysis data
        latest_signal: Signal from the linked analysis
        analysis_date: Date of the linked analysis

    Example:
        >>> item = WatchlistItem(
        ...     ticker="AAPL",
        ...     company_name="Apple Inc.",
        ...     portfolio_name="My Portfolio",
        ...     analysis_id=42,
        ...     target_price=150.0
        ... )
    """

    ticker: str
    company_name: Optional[str]
    portfolio_name: str
    analysis_id: Optional[int] = None
    target_price: Optional[float] = None
    notes: Optional[str] = None
    added_at: Optional[datetime] = None
    id: Optional[int] = None

    # Populated from analysis_history when loaded
    latest_signal: Optional[str] = None
    analysis_date: Optional[datetime] = None

    def __post_init__(self):
        """Validate and normalize watchlist item data."""
        # Normalize ticker to uppercase
        self.ticker = self.ticker.strip().upper()

        # Validate target_price if provided
        if self.target_price is not None and self.target_price <= 0:
            logger.warning(
                "invalid_target_price",
                ticker=self.ticker,
                price=self.target_price,
                msg="Target price should be positive"
            )

        # Set added_at if not provided
        if self.added_at is None:
            self.added_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "portfolio_name": self.portfolio_name,
            "analysis_id": self.analysis_id,
            "target_price": self.target_price,
            "notes": self.notes,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "latest_signal": self.latest_signal,
            "analysis_date": self.analysis_date.isoformat() if self.analysis_date else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WatchlistItem":
        """Create a WatchlistItem from a dictionary."""
        added_at = data.get("added_at")
        if isinstance(added_at, str):
            added_at = datetime.fromisoformat(added_at)

        analysis_date = data.get("analysis_date")
        if isinstance(analysis_date, str):
            analysis_date = datetime.fromisoformat(analysis_date)

        return cls(
            id=data.get("id"),
            ticker=data["ticker"],
            company_name=data.get("company_name"),
            portfolio_name=data["portfolio_name"],
            analysis_id=data.get("analysis_id"),
            target_price=data.get("target_price"),
            notes=data.get("notes"),
            added_at=added_at,
            latest_signal=data.get("latest_signal"),
            analysis_date=analysis_date,
        )

    @property
    def has_analysis(self) -> bool:
        """Check if this watchlist item has a linked analysis."""
        return self.analysis_id is not None

    def update_notes(self, notes: str) -> None:
        """Update the notes for this watchlist item."""
        self.notes = notes

    def update_target_price(self, price: float) -> None:
        """Update the target price for this watchlist item."""
        if price <= 0:
            raise ValueError(f"Target price must be positive, got {price}")
        self.target_price = price
