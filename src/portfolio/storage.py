"""
Persistence layer for portfolio data.

This module provides storage capabilities for portfolios, positions, and
transactions using SQLite database with CSV export/import functionality.
"""

import sqlite3
import csv
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import structlog

from .position import Position
from .transaction import Transaction, TransactionType
from .manager import PortfolioManager
from .watchlist import WatchlistItem
from ..exceptions import InvestmentAgentError

logger = structlog.get_logger(__name__)


class StorageError(InvestmentAgentError):
    """Base exception for storage-related errors."""
    pass


class PortfolioStorage:
    """
    Persistent storage for portfolio data using SQLite.

    Provides methods to:
    - Save and load portfolios
    - Save and retrieve transactions
    - Export to CSV
    - Import from CSV

    Example:
        >>> storage = PortfolioStorage("portfolio.db")
        >>> storage.save_portfolio(portfolio_manager)
        >>> loaded = storage.load_portfolio("My Portfolio")
    """

    def __init__(self, db_path: str = "portfolio.db"):
        """
        Initialize portfolio storage.

        Args:
            db_path: Path to SQLite database file

        Example:
            >>> storage = PortfolioStorage("my_portfolio.db")
        """
        self.db_path = db_path
        self._connection = None

        # For in-memory databases, keep persistent connection
        if db_path == ":memory:":
            self._connection = sqlite3.connect(db_path)

        self._init_database()

        logger.info("portfolio_storage_initialized", db_path=self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (reuse for in-memory DBs)."""
        if self._connection:
            return self._connection
        return sqlite3.connect(self.db_path)

    def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            conn = self._get_connection()
            if not self._connection:
                # Use context manager for file-based DBs
                conn = sqlite3.connect(self.db_path)
            with conn:
                cursor = conn.cursor()

                # Create portfolios table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS portfolios (
                        name TEXT PRIMARY KEY,
                        base_currency TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

                # Create positions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS positions (
                        portfolio_name TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        shares REAL NOT NULL,
                        avg_cost REAL NOT NULL,
                        currency TEXT NOT NULL,
                        purchase_date TEXT NOT NULL,
                        current_price REAL,
                        last_updated TEXT,
                        notes TEXT,
                        PRIMARY KEY (portfolio_name, ticker),
                        FOREIGN KEY (portfolio_name) REFERENCES portfolios(name)
                    )
                """)

                # Create transactions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        transaction_id TEXT PRIMARY KEY,
                        portfolio_name TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        transaction_type TEXT NOT NULL,
                        shares REAL NOT NULL,
                        price REAL NOT NULL,
                        fees REAL NOT NULL,
                        date TEXT NOT NULL,
                        currency TEXT NOT NULL,
                        notes TEXT,
                        dividend_amount REAL,
                        FOREIGN KEY (portfolio_name) REFERENCES portfolios(name)
                    )
                """)

                # Create indices for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_transactions_portfolio
                    ON transactions(portfolio_name)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_transactions_ticker
                    ON transactions(ticker)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_transactions_date
                    ON transactions(date)
                """)

                # Create watchlist table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS watchlist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        portfolio_name TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        company_name TEXT,
                        analysis_id INTEGER,
                        target_price REAL,
                        notes TEXT,
                        added_at TEXT NOT NULL,
                        UNIQUE(portfolio_name, ticker),
                        FOREIGN KEY (portfolio_name) REFERENCES portfolios(name)
                    )
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_watchlist_portfolio
                    ON watchlist(portfolio_name)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_watchlist_ticker
                    ON watchlist(ticker)
                """)

                conn.commit()

                logger.debug("database_schema_initialized")

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to initialize database",
                details={"db_path": self.db_path},
                cause=e
            )

    def save_portfolio(self, manager: PortfolioManager) -> None:
        """
        Save portfolio to database.

        Saves portfolio metadata, all positions, and all transactions.

        Args:
            manager: PortfolioManager to save

        Raises:
            StorageError: If save operation fails

        Example:
            >>> storage.save_portfolio(portfolio_manager)
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)
            with conn:
                cursor = conn.cursor()

                # Save or update portfolio metadata
                cursor.execute("""
                    INSERT OR REPLACE INTO portfolios (name, base_currency, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    manager.name,
                    manager.base_currency,
                    manager._created_at.isoformat(),
                    datetime.now().isoformat()
                ))

                # Delete existing positions for this portfolio
                cursor.execute("""
                    DELETE FROM positions WHERE portfolio_name = ?
                """, (manager.name,))

                # Save all positions
                for position in manager.positions.values():
                    cursor.execute("""
                        INSERT INTO positions (
                            portfolio_name, ticker, shares, avg_cost, currency,
                            purchase_date, current_price, last_updated, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        manager.name,
                        position.ticker,
                        position.shares,
                        position.avg_cost,
                        position.currency,
                        position.purchase_date.isoformat(),
                        position.current_price,
                        position.last_updated.isoformat() if position.last_updated else None,
                        position.notes
                    ))

                # Save new transactions (skip existing ones)
                for transaction in manager.transactions:
                    cursor.execute("""
                        INSERT OR IGNORE INTO transactions (
                            transaction_id, portfolio_name, ticker, transaction_type,
                            shares, price, fees, date, currency, notes, dividend_amount
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        transaction.transaction_id,
                        manager.name,
                        transaction.ticker,
                        transaction.transaction_type.value,
                        transaction.shares,
                        transaction.price,
                        transaction.fees,
                        transaction.date.isoformat(),
                        transaction.currency,
                        transaction.notes,
                        transaction.dividend_amount
                    ))

                conn.commit()

                logger.info(
                    "portfolio_saved",
                    portfolio_name=manager.name,
                    positions=len(manager.positions),
                    transactions=len(manager.transactions)
                )

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to save portfolio",
                details={"portfolio_name": manager.name},
                cause=e
            )

    def load_portfolio(self, name: str) -> Optional[PortfolioManager]:
        """
        Load portfolio from database.

        Args:
            name: Portfolio name

        Returns:
            PortfolioManager if found, None otherwise

        Example:
            >>> manager = storage.load_portfolio("My Portfolio")
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)
            with conn:
                cursor = conn.cursor()

                # Load portfolio metadata
                cursor.execute("""
                    SELECT name, base_currency, created_at
                    FROM portfolios WHERE name = ?
                """, (name,))

                row = cursor.fetchone()
                if not row:
                    logger.warning("portfolio_not_found", name=name)
                    return None

                portfolio_name, base_currency, created_at = row

                # Create portfolio manager
                manager = PortfolioManager(name=portfolio_name, base_currency=base_currency)
                manager._created_at = datetime.fromisoformat(created_at)

                # Load positions
                cursor.execute("""
                    SELECT ticker, shares, avg_cost, currency, purchase_date,
                           current_price, last_updated, notes
                    FROM positions WHERE portfolio_name = ?
                """, (name,))

                for row in cursor.fetchall():
                    ticker, shares, avg_cost, currency, purchase_date, current_price, last_updated, notes = row

                    position = Position(
                        ticker=ticker,
                        shares=shares,
                        avg_cost=avg_cost,
                        currency=currency,
                        purchase_date=datetime.fromisoformat(purchase_date),
                        current_price=current_price,
                        last_updated=datetime.fromisoformat(last_updated) if last_updated else None,
                        notes=notes
                    )

                    manager._positions[position.ticker] = position

                # Load transactions
                cursor.execute("""
                    SELECT transaction_id, ticker, transaction_type, shares, price,
                           fees, date, currency, notes, dividend_amount
                    FROM transactions WHERE portfolio_name = ?
                    ORDER BY date ASC
                """, (name,))

                for row in cursor.fetchall():
                    (transaction_id, ticker, transaction_type, shares, price,
                     fees, date, currency, notes, dividend_amount) = row

                    transaction = Transaction(
                        transaction_id=transaction_id,
                        ticker=ticker,
                        transaction_type=TransactionType(transaction_type),
                        shares=shares,
                        price=price,
                        fees=fees,
                        date=datetime.fromisoformat(date),
                        currency=currency,
                        notes=notes,
                        dividend_amount=dividend_amount
                    )

                    manager._transactions.append(transaction)

                logger.info(
                    "portfolio_loaded",
                    portfolio_name=name,
                    positions=len(manager.positions),
                    transactions=len(manager.transactions)
                )

                return manager

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to load portfolio",
                details={"portfolio_name": name},
                cause=e
            )

    def list_portfolios(self) -> List[str]:
        """
        List all saved portfolios.

        Returns:
            List of portfolio names

        Example:
            >>> portfolios = storage.list_portfolios()
            >>> print(portfolios)
            ['My Portfolio', 'Retirement Account']
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM portfolios ORDER BY name")
                return [row[0] for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to list portfolios",
                cause=e
            )

    def delete_portfolio(self, name: str) -> bool:
        """
        Delete portfolio from database.

        Args:
            name: Portfolio name

        Returns:
            True if deleted, False if not found

        Example:
            >>> storage.delete_portfolio("Old Portfolio")
            True
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)
            with conn:
                cursor = conn.cursor()

                # Delete transactions
                cursor.execute("DELETE FROM transactions WHERE portfolio_name = ?", (name,))

                # Delete positions
                cursor.execute("DELETE FROM positions WHERE portfolio_name = ?", (name,))

                # Delete portfolio
                cursor.execute("DELETE FROM portfolios WHERE name = ?", (name,))

                deleted = cursor.rowcount > 0
                conn.commit()

                if deleted:
                    logger.info("portfolio_deleted", name=name)
                else:
                    logger.warning("portfolio_not_found_for_deletion", name=name)

                return deleted

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to delete portfolio",
                details={"portfolio_name": name},
                cause=e
            )

    def save_transaction(self, portfolio_name: str, transaction: Transaction) -> None:
        """
        Save a single transaction.

        Args:
            portfolio_name: Name of portfolio
            transaction: Transaction to save

        Example:
            >>> storage.save_transaction("My Portfolio", transaction)
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)
            with conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO transactions (
                        transaction_id, portfolio_name, ticker, transaction_type,
                        shares, price, fees, date, currency, notes, dividend_amount
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction.transaction_id,
                    portfolio_name,
                    transaction.ticker,
                    transaction.transaction_type.value,
                    transaction.shares,
                    transaction.price,
                    transaction.fees,
                    transaction.date.isoformat(),
                    transaction.currency,
                    transaction.notes,
                    transaction.dividend_amount
                ))

                conn.commit()

                logger.debug(
                    "transaction_saved",
                    transaction_id=transaction.transaction_id,
                    portfolio=portfolio_name
                )

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to save transaction",
                details={
                    "portfolio_name": portfolio_name,
                    "transaction_id": transaction.transaction_id
                },
                cause=e
            )

    def get_transactions(
        self,
        portfolio_name: str,
        ticker: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """
        Get transactions from database.

        Args:
            portfolio_name: Name of portfolio
            ticker: Filter by ticker (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)

        Returns:
            List of transactions

        Example:
            >>> transactions = storage.get_transactions("My Portfolio", ticker="AAPL")
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)
            with conn:
                cursor = conn.cursor()

                # Build query with filters
                query = """
                    SELECT transaction_id, ticker, transaction_type, shares, price,
                           fees, date, currency, notes, dividend_amount
                    FROM transactions
                    WHERE portfolio_name = ?
                """
                params = [portfolio_name]

                if ticker:
                    query += " AND ticker = ?"
                    params.append(ticker.upper())

                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date.isoformat())

                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date.isoformat())

                query += " ORDER BY date ASC"

                cursor.execute(query, params)

                transactions = []
                for row in cursor.fetchall():
                    (transaction_id, ticker, transaction_type, shares, price,
                     fees, date, currency, notes, dividend_amount) = row

                    transaction = Transaction(
                        transaction_id=transaction_id,
                        ticker=ticker,
                        transaction_type=TransactionType(transaction_type),
                        shares=shares,
                        price=price,
                        fees=fees,
                        date=datetime.fromisoformat(date),
                        currency=currency,
                        notes=notes,
                        dividend_amount=dividend_amount
                    )
                    transactions.append(transaction)

                return transactions

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to get transactions",
                details={"portfolio_name": portfolio_name},
                cause=e
            )

    def export_to_csv(self, portfolio_name: str, output_dir: str = ".") -> Dict[str, str]:
        """
        Export portfolio to CSV files.

        Creates two CSV files:
        - {portfolio_name}_positions.csv
        - {portfolio_name}_transactions.csv

        Args:
            portfolio_name: Name of portfolio to export
            output_dir: Output directory (default current directory)

        Returns:
            Dictionary with paths to created files

        Example:
            >>> files = storage.export_to_csv("My Portfolio", "/tmp")
            >>> print(files['positions'])
            /tmp/My_Portfolio_positions.csv
        """
        manager = self.load_portfolio(portfolio_name)
        if not manager:
            raise StorageError(
                f"Portfolio '{portfolio_name}' not found",
                details={"portfolio_name": portfolio_name}
            )

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_name = portfolio_name.replace(" ", "_").replace("/", "_")

        # Export positions
        positions_file = output_path / f"{safe_name}_positions.csv"
        with open(positions_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ticker', 'shares', 'avg_cost', 'currency', 'purchase_date',
                'current_price', 'current_value', 'total_cost', 'unrealized_pnl',
                'unrealized_pnl_pct', 'notes'
            ])

            for position in manager.positions.values():
                writer.writerow([
                    position.ticker,
                    position.shares,
                    position.avg_cost,
                    position.currency,
                    position.purchase_date.date().isoformat(),
                    position.current_price or '',
                    position.current_value or '',
                    position.total_cost,
                    position.unrealized_pnl or '',
                    position.unrealized_pnl_pct or '',
                    position.notes or ''
                ])

        # Export transactions
        transactions_file = output_path / f"{safe_name}_transactions.csv"
        with open(transactions_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'transaction_id', 'ticker', 'type', 'shares', 'price',
                'fees', 'date', 'currency', 'dividend_amount', 'total_amount', 'notes'
            ])

            for txn in manager.transactions:
                writer.writerow([
                    txn.transaction_id,
                    txn.ticker,
                    txn.transaction_type.value,
                    txn.shares,
                    txn.price,
                    txn.fees,
                    txn.date.date().isoformat(),
                    txn.currency,
                    txn.dividend_amount or '',
                    txn.total_amount,
                    txn.notes or ''
                ])

        logger.info(
            "portfolio_exported_to_csv",
            portfolio_name=portfolio_name,
            positions_file=str(positions_file),
            transactions_file=str(transactions_file)
        )

        return {
            "positions": str(positions_file),
            "transactions": str(transactions_file)
        }

    def import_from_csv(
        self,
        portfolio_name: str,
        positions_file: Optional[str] = None,
        transactions_file: Optional[str] = None,
        base_currency: str = "USD"
    ) -> PortfolioManager:
        """
        Import portfolio from CSV files.

        Args:
            portfolio_name: Name for the portfolio
            positions_file: Path to positions CSV (optional)
            transactions_file: Path to transactions CSV (optional)
            base_currency: Base currency (default "USD")

        Returns:
            Loaded PortfolioManager

        Example:
            >>> manager = storage.import_from_csv(
            ...     "Imported Portfolio",
            ...     positions_file="positions.csv",
            ...     transactions_file="transactions.csv"
            ... )
        """
        manager = PortfolioManager(name=portfolio_name, base_currency=base_currency)

        # Import positions
        if positions_file:
            with open(positions_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    position = Position(
                        ticker=row['ticker'],
                        shares=float(row['shares']),
                        avg_cost=float(row['avg_cost']),
                        currency=row['currency'],
                        purchase_date=datetime.fromisoformat(row['purchase_date']),
                        current_price=float(row['current_price']) if row['current_price'] else None,
                        notes=row.get('notes') or None
                    )
                    manager._positions[position.ticker] = position

        # Import transactions
        if transactions_file:
            with open(transactions_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    transaction = Transaction(
                        transaction_id=row.get('transaction_id'),
                        ticker=row['ticker'],
                        transaction_type=TransactionType(row['type']),
                        shares=float(row['shares']),
                        price=float(row['price']),
                        fees=float(row['fees']),
                        date=datetime.fromisoformat(row['date']),
                        currency=row['currency'],
                        notes=row.get('notes') or None,
                        dividend_amount=float(row['dividend_amount']) if row.get('dividend_amount') else None
                    )
                    manager._transactions.append(transaction)

        # Save to database
        self.save_portfolio(manager)

        logger.info(
            "portfolio_imported_from_csv",
            portfolio_name=portfolio_name,
            positions=len(manager.positions),
            transactions=len(manager.transactions)
        )

        return manager

    # =========================================================================
    # Watchlist Methods
    # =========================================================================

    def add_to_watchlist(self, item: WatchlistItem) -> int:
        """
        Add a stock to the watchlist.

        Args:
            item: WatchlistItem to add

        Returns:
            Database ID of the created watchlist item

        Raises:
            StorageError: If add operation fails (e.g., duplicate)

        Example:
            >>> item = WatchlistItem(ticker="AAPL", company_name="Apple Inc.",
            ...                      portfolio_name="My Portfolio", analysis_id=42)
            >>> item_id = storage.add_to_watchlist(item)
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)

            with conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO watchlist (
                        portfolio_name, ticker, company_name, analysis_id,
                        target_price, notes, added_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.portfolio_name,
                    item.ticker,
                    item.company_name,
                    item.analysis_id,
                    item.target_price,
                    item.notes,
                    item.added_at.isoformat() if item.added_at else datetime.now().isoformat()
                ))

                conn.commit()
                item_id = cursor.lastrowid

                logger.info(
                    "watchlist_item_added",
                    id=item_id,
                    ticker=item.ticker,
                    portfolio=item.portfolio_name
                )

                return item_id

        except sqlite3.IntegrityError as e:
            raise StorageError(
                "Stock already in watchlist",
                details={"ticker": item.ticker, "portfolio": item.portfolio_name},
                cause=e
            )
        except sqlite3.Error as e:
            raise StorageError(
                "Failed to add to watchlist",
                details={"ticker": item.ticker},
                cause=e
            )

    def remove_from_watchlist(self, portfolio_name: str, ticker: str) -> bool:
        """
        Remove a stock from the watchlist.

        Args:
            portfolio_name: Name of the portfolio
            ticker: Stock ticker to remove

        Returns:
            True if removed, False if not found

        Example:
            >>> storage.remove_from_watchlist("My Portfolio", "AAPL")
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)

            with conn:
                cursor = conn.cursor()

                ticker = ticker.strip().upper()

                cursor.execute("""
                    DELETE FROM watchlist
                    WHERE portfolio_name = ? AND ticker = ?
                """, (portfolio_name, ticker))

                conn.commit()
                deleted = cursor.rowcount > 0

                if deleted:
                    logger.info(
                        "watchlist_item_removed",
                        ticker=ticker,
                        portfolio=portfolio_name
                    )

                return deleted

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to remove from watchlist",
                details={"ticker": ticker, "portfolio": portfolio_name},
                cause=e
            )

    def get_watchlist(self, portfolio_name: str) -> List[WatchlistItem]:
        """
        Get all watchlist items for a portfolio.

        Args:
            portfolio_name: Name of the portfolio

        Returns:
            List of WatchlistItems with analysis data populated

        Example:
            >>> items = storage.get_watchlist("My Portfolio")
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)

            cursor = conn.cursor()

            # Join with analysis_history to get signal and date
            cursor.execute("""
                SELECT w.id, w.portfolio_name, w.ticker, w.company_name,
                       w.analysis_id, w.target_price, w.notes, w.added_at,
                       a.signal, a.analysis_date
                FROM watchlist w
                LEFT JOIN analysis_history a ON w.analysis_id = a.id
                WHERE w.portfolio_name = ?
                ORDER BY w.added_at DESC
            """, (portfolio_name,))

            items = []
            for row in cursor.fetchall():
                item = WatchlistItem(
                    id=row[0],
                    portfolio_name=row[1],
                    ticker=row[2],
                    company_name=row[3],
                    analysis_id=row[4],
                    target_price=row[5],
                    notes=row[6],
                    added_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    latest_signal=row[8],
                    analysis_date=datetime.fromisoformat(row[9]) if row[9] else None
                )
                items.append(item)

            return items

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to get watchlist",
                details={"portfolio": portfolio_name},
                cause=e
            )

    def get_watchlist_item(self, portfolio_name: str, ticker: str) -> Optional[WatchlistItem]:
        """
        Get a specific watchlist item.

        Args:
            portfolio_name: Name of the portfolio
            ticker: Stock ticker

        Returns:
            WatchlistItem if found, None otherwise
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)

            cursor = conn.cursor()
            ticker = ticker.strip().upper()

            cursor.execute("""
                SELECT w.id, w.portfolio_name, w.ticker, w.company_name,
                       w.analysis_id, w.target_price, w.notes, w.added_at,
                       a.signal, a.analysis_date
                FROM watchlist w
                LEFT JOIN analysis_history a ON w.analysis_id = a.id
                WHERE w.portfolio_name = ? AND w.ticker = ?
            """, (portfolio_name, ticker))

            row = cursor.fetchone()
            if row:
                return WatchlistItem(
                    id=row[0],
                    portfolio_name=row[1],
                    ticker=row[2],
                    company_name=row[3],
                    analysis_id=row[4],
                    target_price=row[5],
                    notes=row[6],
                    added_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    latest_signal=row[8],
                    analysis_date=datetime.fromisoformat(row[9]) if row[9] else None
                )
            return None

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to get watchlist item",
                details={"ticker": ticker, "portfolio": portfolio_name},
                cause=e
            )

    def update_watchlist_item(
        self,
        portfolio_name: str,
        ticker: str,
        target_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update a watchlist item's target price or notes.

        Args:
            portfolio_name: Name of the portfolio
            ticker: Stock ticker
            target_price: New target price (or None to keep unchanged)
            notes: New notes (or None to keep unchanged)

        Returns:
            True if updated, False if not found
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)

            with conn:
                cursor = conn.cursor()
                ticker = ticker.strip().upper()

                updates = []
                params = []

                if target_price is not None:
                    updates.append("target_price = ?")
                    params.append(target_price)

                if notes is not None:
                    updates.append("notes = ?")
                    params.append(notes)

                if not updates:
                    return False

                params.extend([portfolio_name, ticker])

                cursor.execute(f"""
                    UPDATE watchlist
                    SET {", ".join(updates)}
                    WHERE portfolio_name = ? AND ticker = ?
                """, params)

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to update watchlist item",
                details={"ticker": ticker, "portfolio": portfolio_name},
                cause=e
            )

    def convert_watchlist_to_position(
        self,
        portfolio_name: str,
        ticker: str,
        shares: float,
        price: float,
        fees: float = 0.0,
        currency: str = "USD",
        notes: Optional[str] = None
    ) -> bool:
        """
        Convert a watchlist item to an actual position.

        This creates a buy transaction, adds/updates the position,
        and removes the item from the watchlist.

        Args:
            portfolio_name: Name of the portfolio
            ticker: Stock ticker to convert
            shares: Number of shares to buy
            price: Purchase price per share
            fees: Transaction fees
            currency: Currency code
            notes: Optional transaction notes

        Returns:
            True if successful

        Raises:
            StorageError: If conversion fails
        """
        try:
            # First check if item exists in watchlist
            item = self.get_watchlist_item(portfolio_name, ticker)
            if not item:
                raise StorageError(
                    "Watchlist item not found",
                    details={"ticker": ticker, "portfolio": portfolio_name}
                )

            # Load portfolio
            manager = self.load_portfolio(portfolio_name)
            if not manager:
                raise StorageError(
                    "Portfolio not found",
                    details={"portfolio": portfolio_name}
                )

            # Create buy transaction
            from .transaction import create_buy_transaction
            transaction = create_buy_transaction(
                ticker=ticker,
                shares=shares,
                price=price,
                fees=fees,
                currency=currency,
                notes=notes or f"Converted from watchlist"
            )

            # Add position or update existing
            if manager.has_position(ticker):
                position = manager.get_position(ticker)
                position.add_shares(shares, price)
            else:
                position = Position(
                    ticker=ticker,
                    shares=shares,
                    avg_cost=price,
                    currency=currency,
                    purchase_date=datetime.now(),
                    current_price=price,
                    notes=item.notes
                )
                manager.add_position(position)

            # Record transaction
            manager.record_transaction(transaction)

            # Save portfolio
            self.save_portfolio(manager)

            # Remove from watchlist
            self.remove_from_watchlist(portfolio_name, ticker)

            logger.info(
                "watchlist_converted_to_position",
                ticker=ticker,
                portfolio=portfolio_name,
                shares=shares,
                price=price
            )

            return True

        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                "Failed to convert watchlist to position",
                details={"ticker": ticker, "portfolio": portfolio_name},
                cause=e
            )

    def is_in_watchlist(self, portfolio_name: str, ticker: str) -> bool:
        """
        Check if a ticker is in the watchlist.

        Args:
            portfolio_name: Name of the portfolio
            ticker: Stock ticker to check

        Returns:
            True if in watchlist, False otherwise
        """
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)

            cursor = conn.cursor()
            ticker = ticker.strip().upper()

            cursor.execute("""
                SELECT 1 FROM watchlist
                WHERE portfolio_name = ? AND ticker = ?
            """, (portfolio_name, ticker))

            return cursor.fetchone() is not None

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to check watchlist",
                details={"ticker": ticker, "portfolio": portfolio_name},
                cause=e
            )
