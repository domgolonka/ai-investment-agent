"""
Analysis history persistence layer.

This module provides storage capabilities for stock analysis results,
enabling users to browse past analyses and create portfolios from them.
"""

import sqlite3
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import structlog

from ..exceptions import InvestmentAgentError

logger = structlog.get_logger(__name__)


class AnalysisHistoryError(InvestmentAgentError):
    """Base exception for analysis history errors."""
    pass


@dataclass
class AnalysisRecord:
    """
    Represents a stored stock analysis.

    Attributes:
        ticker: Stock ticker symbol
        company_name: Full company name
        analysis_date: When the analysis was performed
        analysis_mode: 'quick' or 'deep' analysis mode
        market_report: Market/technical analysis report
        sentiment_report: Sentiment analysis report
        news_report: News-based analysis report
        fundamentals_report: Financial fundamentals report
        investment_plan: Investment plan from analysis
        trader_investment_plan: Trader's investment plan
        final_trade_decision: Final BUY/SELL/HOLD decision text
        consultant_review: Consultant review text
        investment_debate_state: Bull vs Bear debate state (dict)
        risk_debate_state: Risk assessment debate state (dict)
        red_flags: List of detected red flags
        pre_screening_result: 'PASS' or 'REJECT'
        signal: Extracted signal ('BUY', 'SELL', 'HOLD', 'UNKNOWN')
        id: Database ID (set after save)
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Example:
        >>> record = AnalysisRecord.from_agent_state(
        ...     state=analysis_result,
        ...     ticker="AAPL",
        ...     company_name="Apple Inc.",
        ...     mode="deep"
        ... )
        >>> storage.save_analysis(record)
    """

    ticker: str
    company_name: str
    analysis_date: datetime
    analysis_mode: str

    # Reports
    market_report: Optional[str] = None
    sentiment_report: Optional[str] = None
    news_report: Optional[str] = None
    fundamentals_report: Optional[str] = None
    investment_plan: Optional[str] = None
    trader_investment_plan: Optional[str] = None
    final_trade_decision: Optional[str] = None
    consultant_review: Optional[str] = None

    # States (stored as dicts, serialized to JSON)
    investment_debate_state: Optional[Dict[str, Any]] = None
    risk_debate_state: Optional[Dict[str, Any]] = None

    # Red flags
    red_flags: Optional[List[Dict[str, Any]]] = None
    pre_screening_result: Optional[str] = None

    # Extracted signal for filtering
    signal: str = "UNKNOWN"

    # Database fields
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate and normalize analysis data."""
        self.ticker = self.ticker.strip().upper()
        self.analysis_mode = self.analysis_mode.lower()

        if self.analysis_mode not in ("quick", "deep"):
            logger.warning(
                "unknown_analysis_mode",
                mode=self.analysis_mode,
                msg="Expected 'quick' or 'deep', defaulting to 'quick'"
            )
            self.analysis_mode = "quick"

        # Extract signal if not already set
        if self.signal == "UNKNOWN" and self.final_trade_decision:
            self.signal = self._extract_signal(self.final_trade_decision)

        # Set timestamps if not provided
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    @staticmethod
    def _extract_signal(decision_text: str) -> str:
        """Extract BUY/SELL/HOLD signal from decision text."""
        if not decision_text:
            return "UNKNOWN"

        text = decision_text.upper()

        # Priority patterns
        patterns = [
            (r"ACTION:\s*(BUY|SELL|HOLD)", 1),
            (r"FINAL DECISION:\s*(BUY|SELL|HOLD)", 1),
            (r"DECISION:\s*(BUY|SELL|HOLD)", 1),
            (r"RECOMMENDATION:\s*(BUY|SELL|HOLD)", 1),
        ]

        for pattern, group in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(group)

        # Keyword fallback
        if "BUY" in text and "SELL" not in text:
            return "BUY"
        if "SELL" in text and "BUY" not in text:
            return "SELL"
        if "HOLD" in text:
            return "HOLD"

        return "UNKNOWN"

    @classmethod
    def from_agent_state(
        cls,
        state: Dict[str, Any],
        ticker: str,
        company_name: str,
        mode: str
    ) -> "AnalysisRecord":
        """
        Create an AnalysisRecord from an AgentState result dict.

        Args:
            state: The result dictionary from run_analysis()
            ticker: Stock ticker symbol
            company_name: Full company name
            mode: Analysis mode ('quick' or 'deep')

        Returns:
            AnalysisRecord populated from the state
        """

        def to_string(value: Any) -> Optional[str]:
            """Convert various value types to string."""
            if value is None:
                return None
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                if "text" in value:
                    return value["text"]
                return json.dumps(value)
            if isinstance(value, list):
                parts = []
                for item in value:
                    if isinstance(item, dict) and "text" in item:
                        parts.append(item["text"])
                    else:
                        parts.append(str(item))
                return "\n".join(parts)
            return str(value)

        def to_dict(value: Any) -> Optional[Dict]:
            """Convert value to dict or return None."""
            if value is None:
                return None
            if isinstance(value, dict):
                return value
            if hasattr(value, "__dict__"):
                return vars(value)
            return None

        def to_list(value: Any) -> Optional[List]:
            """Convert value to list or return None."""
            if value is None:
                return None
            if isinstance(value, list):
                return value
            return [value]

        return cls(
            ticker=ticker,
            company_name=company_name,
            analysis_date=datetime.now(),
            analysis_mode=mode,
            market_report=to_string(state.get("market_report")),
            sentiment_report=to_string(state.get("sentiment_report")),
            news_report=to_string(state.get("news_report")),
            fundamentals_report=to_string(state.get("fundamentals_report")),
            investment_plan=to_string(state.get("investment_plan")),
            trader_investment_plan=to_string(state.get("trader_investment_plan")),
            final_trade_decision=to_string(state.get("final_trade_decision")),
            consultant_review=to_string(state.get("consultant_review")),
            investment_debate_state=to_dict(state.get("investment_debate_state")),
            risk_debate_state=to_dict(state.get("risk_debate_state")),
            red_flags=to_list(state.get("red_flags")),
            pre_screening_result=state.get("pre_screening_result"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "analysis_date": self.analysis_date.isoformat() if self.analysis_date else None,
            "analysis_mode": self.analysis_mode,
            "market_report": self.market_report,
            "sentiment_report": self.sentiment_report,
            "news_report": self.news_report,
            "fundamentals_report": self.fundamentals_report,
            "investment_plan": self.investment_plan,
            "trader_investment_plan": self.trader_investment_plan,
            "final_trade_decision": self.final_trade_decision,
            "consultant_review": self.consultant_review,
            "investment_debate_state": self.investment_debate_state,
            "risk_debate_state": self.risk_debate_state,
            "red_flags": self.red_flags,
            "pre_screening_result": self.pre_screening_result,
            "signal": self.signal,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AnalysisHistoryStorage:
    """
    Persistent storage for analysis history using SQLite.

    Provides methods to:
    - Save analysis records
    - Retrieve by ID or ticker
    - Search with filters
    - Delete records

    Example:
        >>> storage = AnalysisHistoryStorage("portfolio.db")
        >>> analysis_id = storage.save_analysis(record)
        >>> analyses = storage.get_recent_analyses(limit=10, signal_filter="BUY")
    """

    def __init__(self, db_path: str = "demo_portfolio.db"):
        """
        Initialize analysis history storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._connection = None

        # For in-memory databases, keep persistent connection
        if db_path == ":memory:":
            self._connection = sqlite3.connect(db_path)

        self._init_database()
        logger.info("analysis_history_storage_initialized", db_path=self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (reuse for in-memory DBs)."""
        if self._connection:
            return self._connection
        return sqlite3.connect(self.db_path)

    def _init_database(self) -> None:
        """Initialize database schema for analysis history."""
        try:
            conn = self._get_connection()
            if not self._connection:
                conn = sqlite3.connect(self.db_path)

            with conn:
                cursor = conn.cursor()

                # Create analysis_history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticker TEXT NOT NULL,
                        company_name TEXT NOT NULL,
                        analysis_date TEXT NOT NULL,
                        analysis_mode TEXT NOT NULL,

                        market_report TEXT,
                        sentiment_report TEXT,
                        news_report TEXT,
                        fundamentals_report TEXT,
                        investment_plan TEXT,
                        trader_investment_plan TEXT,
                        final_trade_decision TEXT,
                        consultant_review TEXT,

                        investment_debate_state TEXT,
                        risk_debate_state TEXT,

                        red_flags TEXT,
                        pre_screening_result TEXT,

                        signal TEXT,

                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

                # Create indices for efficient querying
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analysis_history_ticker
                    ON analysis_history(ticker)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analysis_history_date
                    ON analysis_history(analysis_date)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analysis_history_signal
                    ON analysis_history(signal)
                """)

                conn.commit()
                logger.debug("analysis_history_schema_initialized")

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to initialize analysis history database",
                details={"db_path": self.db_path},
                cause=e
            )

    def save_analysis(self, record: AnalysisRecord) -> int:
        """
        Save an analysis record to the database.

        Args:
            record: AnalysisRecord to save

        Returns:
            The database ID of the saved record

        Raises:
            AnalysisHistoryError: If save fails
        """
        try:
            conn = self._get_connection()
            with conn:
                cursor = conn.cursor()

                # Serialize JSON fields
                investment_debate_json = json.dumps(record.investment_debate_state) if record.investment_debate_state else None
                risk_debate_json = json.dumps(record.risk_debate_state) if record.risk_debate_state else None
                red_flags_json = json.dumps(record.red_flags) if record.red_flags else None

                now = datetime.now().isoformat()

                cursor.execute("""
                    INSERT INTO analysis_history (
                        ticker, company_name, analysis_date, analysis_mode,
                        market_report, sentiment_report, news_report, fundamentals_report,
                        investment_plan, trader_investment_plan, final_trade_decision, consultant_review,
                        investment_debate_state, risk_debate_state,
                        red_flags, pre_screening_result,
                        signal, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.ticker,
                    record.company_name,
                    record.analysis_date.isoformat(),
                    record.analysis_mode,
                    record.market_report,
                    record.sentiment_report,
                    record.news_report,
                    record.fundamentals_report,
                    record.investment_plan,
                    record.trader_investment_plan,
                    record.final_trade_decision,
                    record.consultant_review,
                    investment_debate_json,
                    risk_debate_json,
                    red_flags_json,
                    record.pre_screening_result,
                    record.signal,
                    now,
                    now
                ))

                conn.commit()
                analysis_id = cursor.lastrowid

                logger.info(
                    "analysis_saved",
                    id=analysis_id,
                    ticker=record.ticker,
                    signal=record.signal
                )

                return analysis_id

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to save analysis",
                details={"ticker": record.ticker},
                cause=e
            )

    def _row_to_record(self, row: tuple) -> AnalysisRecord:
        """Convert a database row to an AnalysisRecord."""
        return AnalysisRecord(
            id=row[0],
            ticker=row[1],
            company_name=row[2],
            analysis_date=datetime.fromisoformat(row[3]),
            analysis_mode=row[4],
            market_report=row[5],
            sentiment_report=row[6],
            news_report=row[7],
            fundamentals_report=row[8],
            investment_plan=row[9],
            trader_investment_plan=row[10],
            final_trade_decision=row[11],
            consultant_review=row[12],
            investment_debate_state=json.loads(row[13]) if row[13] else None,
            risk_debate_state=json.loads(row[14]) if row[14] else None,
            red_flags=json.loads(row[15]) if row[15] else None,
            pre_screening_result=row[16],
            signal=row[17] or "UNKNOWN",
            created_at=datetime.fromisoformat(row[18]) if row[18] else None,
            updated_at=datetime.fromisoformat(row[19]) if row[19] else None,
        )

    def get_analysis_by_id(self, analysis_id: int) -> Optional[AnalysisRecord]:
        """
        Get a single analysis by its ID.

        Args:
            analysis_id: Database ID of the analysis

        Returns:
            AnalysisRecord if found, None otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, ticker, company_name, analysis_date, analysis_mode,
                       market_report, sentiment_report, news_report, fundamentals_report,
                       investment_plan, trader_investment_plan, final_trade_decision, consultant_review,
                       investment_debate_state, risk_debate_state,
                       red_flags, pre_screening_result,
                       signal, created_at, updated_at
                FROM analysis_history
                WHERE id = ?
            """, (analysis_id,))

            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            return None

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to get analysis by ID",
                details={"analysis_id": analysis_id},
                cause=e
            )

    def get_analyses_for_ticker(
        self,
        ticker: str,
        limit: int = 10
    ) -> List[AnalysisRecord]:
        """
        Get all analyses for a specific ticker, most recent first.

        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of records to return

        Returns:
            List of AnalysisRecords
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            ticker = ticker.strip().upper()

            cursor.execute("""
                SELECT id, ticker, company_name, analysis_date, analysis_mode,
                       market_report, sentiment_report, news_report, fundamentals_report,
                       investment_plan, trader_investment_plan, final_trade_decision, consultant_review,
                       investment_debate_state, risk_debate_state,
                       red_flags, pre_screening_result,
                       signal, created_at, updated_at
                FROM analysis_history
                WHERE ticker = ?
                ORDER BY analysis_date DESC
                LIMIT ?
            """, (ticker, limit))

            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to get analyses for ticker",
                details={"ticker": ticker},
                cause=e
            )

    def get_recent_analyses(
        self,
        limit: int = 50,
        signal_filter: Optional[str] = None
    ) -> List[AnalysisRecord]:
        """
        Get recent analyses with optional signal filtering.

        Args:
            limit: Maximum number of records to return
            signal_filter: Filter by signal ('BUY', 'SELL', 'HOLD')

        Returns:
            List of AnalysisRecords, most recent first
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if signal_filter:
                signal_filter = signal_filter.strip().upper()
                cursor.execute("""
                    SELECT id, ticker, company_name, analysis_date, analysis_mode,
                           market_report, sentiment_report, news_report, fundamentals_report,
                           investment_plan, trader_investment_plan, final_trade_decision, consultant_review,
                           investment_debate_state, risk_debate_state,
                           red_flags, pre_screening_result,
                           signal, created_at, updated_at
                    FROM analysis_history
                    WHERE signal = ?
                    ORDER BY analysis_date DESC
                    LIMIT ?
                """, (signal_filter, limit))
            else:
                cursor.execute("""
                    SELECT id, ticker, company_name, analysis_date, analysis_mode,
                           market_report, sentiment_report, news_report, fundamentals_report,
                           investment_plan, trader_investment_plan, final_trade_decision, consultant_review,
                           investment_debate_state, risk_debate_state,
                           red_flags, pre_screening_result,
                           signal, created_at, updated_at
                    FROM analysis_history
                    ORDER BY analysis_date DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to get recent analyses",
                details={"limit": limit, "signal_filter": signal_filter},
                cause=e
            )

    def search_analyses(
        self,
        ticker: Optional[str] = None,
        signal: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[AnalysisRecord]:
        """
        Search analyses with multiple filters.

        Args:
            ticker: Filter by ticker (partial match)
            signal: Filter by signal type
            start_date: Filter by analysis date >= start_date
            end_date: Filter by analysis date <= end_date
            limit: Maximum number of records to return

        Returns:
            List of matching AnalysisRecords
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            conditions = []
            params = []

            if ticker:
                conditions.append("ticker LIKE ?")
                params.append(f"%{ticker.strip().upper()}%")

            if signal:
                conditions.append("signal = ?")
                params.append(signal.strip().upper())

            if start_date:
                conditions.append("analysis_date >= ?")
                params.append(start_date.isoformat())

            if end_date:
                conditions.append("analysis_date <= ?")
                params.append(end_date.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            params.append(limit)

            cursor.execute(f"""
                SELECT id, ticker, company_name, analysis_date, analysis_mode,
                       market_report, sentiment_report, news_report, fundamentals_report,
                       investment_plan, trader_investment_plan, final_trade_decision, consultant_review,
                       investment_debate_state, risk_debate_state,
                       red_flags, pre_screening_result,
                       signal, created_at, updated_at
                FROM analysis_history
                WHERE {where_clause}
                ORDER BY analysis_date DESC
                LIMIT ?
            """, params)

            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to search analyses",
                details={"ticker": ticker, "signal": signal},
                cause=e
            )

    def delete_analysis(self, analysis_id: int) -> bool:
        """
        Delete an analysis record.

        Args:
            analysis_id: Database ID of the analysis to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            conn = self._get_connection()
            with conn:
                cursor = conn.cursor()

                cursor.execute("""
                    DELETE FROM analysis_history
                    WHERE id = ?
                """, (analysis_id,))

                conn.commit()
                deleted = cursor.rowcount > 0

                if deleted:
                    logger.info("analysis_deleted", id=analysis_id)

                return deleted

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to delete analysis",
                details={"analysis_id": analysis_id},
                cause=e
            )

    def get_unique_tickers(self) -> List[str]:
        """
        Get list of all unique tickers with analyses.

        Returns:
            List of ticker symbols
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT ticker
                FROM analysis_history
                ORDER BY ticker
            """)

            return [row[0] for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to get unique tickers",
                cause=e
            )

    def get_analysis_count(self) -> int:
        """
        Get total count of analyses.

        Returns:
            Number of analysis records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM analysis_history")
            return cursor.fetchone()[0]

        except sqlite3.Error as e:
            raise AnalysisHistoryError(
                "Failed to get analysis count",
                cause=e
            )
