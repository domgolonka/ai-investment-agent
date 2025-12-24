"""
Portfolio Tracking Module for AI Investment Agent.

This module provides comprehensive portfolio management capabilities including:
- Position tracking with real-time P&L
- Transaction recording and history
- Multi-currency support
- Performance metrics and analytics
- Persistent storage with SQLite
- CSV export/import

Example usage:
    >>> from src.portfolio import (
    ...     Position, Transaction, TransactionType,
    ...     PortfolioManager, PnLCalculator, PortfolioStorage,
    ...     create_buy_transaction, create_sell_transaction
    ... )
    >>>
    >>> # Create a portfolio
    >>> manager = PortfolioManager(name="My Portfolio")
    >>>
    >>> # Add a position
    >>> from datetime import datetime
    >>> position = Position("AAPL", 100, 150.0, "USD", datetime.now())
    >>> manager.add_position(position)
    >>>
    >>> # Record a transaction
    >>> buy = create_buy_transaction("AAPL", 50, 155.0, datetime.now())
    >>> manager.record_transaction(buy)
    >>>
    >>> # Calculate P&L
    >>> calculator = PnLCalculator(manager)
    >>> metrics = calculator.calculate_portfolio_metrics()
    >>>
    >>> # Save to database
    >>> storage = PortfolioStorage("portfolio.db")
    >>> storage.save_portfolio(manager)
"""

from .position import Position
from .transaction import (
    Transaction,
    TransactionType,
    create_buy_transaction,
    create_sell_transaction,
    create_dividend_transaction
)
from .manager import (
    PortfolioManager,
    PortfolioError,
    PositionNotFoundError,
    InsufficientSharesError
)
from .pnl import PnLCalculator
from .storage import PortfolioStorage, StorageError
from .watchlist import WatchlistItem

__all__ = [
    # Position management
    "Position",

    # Transaction management
    "Transaction",
    "TransactionType",
    "create_buy_transaction",
    "create_sell_transaction",
    "create_dividend_transaction",

    # Portfolio manager
    "PortfolioManager",
    "PortfolioError",
    "PositionNotFoundError",
    "InsufficientSharesError",

    # P&L calculator
    "PnLCalculator",

    # Storage
    "PortfolioStorage",
    "StorageError",

    # Watchlist
    "WatchlistItem",
]

__version__ = "1.0.0"
