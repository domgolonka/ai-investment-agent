"""
Base Fetcher Abstract Class

Provides common functionality for all data fetchers:
- Timeout and retry logic
- Standard error handling
- Logging setup
- Abstract methods for fetch and validate
"""

import asyncio
import structlog
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


# Constants
MIN_INFO_FIELDS = 3
ROE_PERCENTAGE_THRESHOLD = 1.0
DEBT_EQUITY_PERCENTAGE_THRESHOLD = 100.0
PRICE_TO_BOOK_CURRENCY_MISMATCH_THRESHOLD = 5.0
FX_CACHE_TTL_SECONDS = 3600
PER_SOURCE_TIMEOUT = 15

# Source quality rankings (higher = more reliable)
SOURCE_QUALITY: Dict[str, float] = {
    'yfinance_statements': 10,        # Calculated directly from filings (Highest trust)
    'calculated_from_statements': 10,  # Tag used by extraction logic
    'eodhd': 9.5,                      # Professional paid feed (High trust for Int'l)
    'yfinance': 9,                     # Standard feed
    'yfinance_info': 9,                # Standard feed
    'alpha_vantage': 9,                # High-quality fundamentals (Int'l)
    'calculated': 8,                   # Derived metrics
    'fmp': 7,                          # Good backup
    'fmp_info': 7,
    'yahooquery': 6,                   # Scraped backup
    'yahooquery_info': 6,
    'tavily_extraction': 4,            # Web NLP extraction
    'proxy': 2                         # Estimates
}


@dataclass
class DataQuality:
    """Track data quality and sources."""
    basics_ok: bool = False
    basics_missing: List[str] = field(default_factory=list)
    coverage_pct: float = 0.0
    sources_used: List[str] = field(default_factory=list)
    gaps_filled: int = 0
    suspicious_fields: List[str] = field(default_factory=list)


@dataclass
class FetcherStats:
    """Statistics tracking for fetcher performance."""
    fetches: int = 0
    basics_ok: int = 0
    basics_failed: int = 0
    avg_coverage: float = 0.0
    sources: Dict[str, int] = field(default_factory=lambda: {
        'yfinance': 0,
        'statements': 0,
        'yahooquery': 0,
        'fmp': 0,
        'eodhd': 0,
        'alpha_vantage': 0,
        'web_search': 0,
        'calculated': 0
    })
    gaps_filled: int = 0

    def copy(self) -> Dict[str, Any]:
        """Return a copy of stats as a dictionary."""
        return {
            'fetches': self.fetches,
            'basics_ok': self.basics_ok,
            'basics_failed': self.basics_failed,
            'avg_coverage': self.avg_coverage,
            'sources': self.sources.copy(),
            'gaps_filled': self.gaps_filled,
        }


class BaseFetcher(ABC):
    """
    Abstract base class for all data fetchers.

    Provides common functionality:
    - Timeout handling with configurable limits
    - Retry logic with exponential backoff
    - Standard error handling patterns
    - Logging setup
    """

    DEFAULT_TIMEOUT = 15
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1.0

    def __init__(self, timeout: int = None):
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.logger = structlog.get_logger(self.__class__.__name__)
        self._last_error: Optional[Exception] = None
        self._last_fetch_time: Optional[datetime] = None

    @abstractmethod
    async def fetch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data for a given symbol.

        Args:
            symbol: The ticker symbol to fetch data for

        Returns:
            Dictionary of fetched data or None if fetch failed
        """
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate the fetched data.

        Args:
            data: The data dictionary to validate

        Returns:
            True if data is valid, False otherwise
        """
        pass

    async def fetch_with_timeout(
        self,
        symbol: str,
        timeout: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch data with timeout protection.

        Args:
            symbol: The ticker symbol to fetch
            timeout: Optional timeout override

        Returns:
            Fetched data or None on timeout/error
        """
        effective_timeout = timeout or self.timeout

        try:
            result = await asyncio.wait_for(
                self.fetch(symbol),
                timeout=effective_timeout
            )
            self._last_fetch_time = datetime.now()
            return result

        except asyncio.TimeoutError:
            self.logger.warning(
                "fetch_timeout",
                symbol=symbol,
                timeout=effective_timeout
            )
            self._last_error = TimeoutError(f"Fetch timed out for {symbol}")
            return None

        except asyncio.CancelledError:
            self.logger.warning("fetch_cancelled", symbol=symbol)
            raise

        except Exception as e:
            self.logger.error(
                "fetch_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            self._last_error = e
            return None

    async def fetch_with_retry(
        self,
        symbol: str,
        max_retries: int = None,
        timeout: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch data with retry logic and exponential backoff.

        Args:
            symbol: The ticker symbol to fetch
            max_retries: Maximum number of retry attempts
            timeout: Timeout for each attempt

        Returns:
            Fetched data or None after all retries exhausted
        """
        retries = max_retries or self.MAX_RETRIES

        for attempt in range(retries):
            result = await self.fetch_with_timeout(symbol, timeout)

            if result is not None:
                return result

            if attempt < retries - 1:
                delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                self.logger.info(
                    "fetch_retry",
                    symbol=symbol,
                    attempt=attempt + 1,
                    delay=delay
                )
                await asyncio.sleep(delay)

        self.logger.warning(
            "fetch_retries_exhausted",
            symbol=symbol,
            attempts=retries
        )
        return None

    def get_last_error(self) -> Optional[Exception]:
        """Get the last error that occurred during fetch."""
        return self._last_error

    def get_last_fetch_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful fetch."""
        return self._last_fetch_time

    def is_available(self) -> bool:
        """
        Check if the fetcher is available for use.

        Override this method to implement circuit breaker logic
        or other availability checks.

        Returns:
            True if fetcher is available
        """
        return True


class FXRateCache:
    """
    Thread-safe FX rate cache with TTL.
    """

    def __init__(self, ttl_seconds: int = FX_CACHE_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, float] = {}
        self._expiry: Dict[str, datetime] = {}

    def get(self, from_curr: str, to_curr: str) -> Optional[float]:
        """
        Get cached FX rate if available and not expired.

        Args:
            from_curr: Source currency code
            to_curr: Target currency code

        Returns:
            Cached rate or None if not available/expired
        """
        if not from_curr or not to_curr or from_curr == to_curr:
            return 1.0

        key = f"{from_curr.upper()}_{to_curr.upper()}"
        expiry = self._expiry.get(key)

        if expiry and datetime.now() < expiry:
            return self._cache.get(key)

        return None

    def set(self, from_curr: str, to_curr: str, rate: float) -> None:
        """
        Cache an FX rate.

        Args:
            from_curr: Source currency code
            to_curr: Target currency code
            rate: The exchange rate
        """
        key = f"{from_curr.upper()}_{to_curr.upper()}"
        self._cache[key] = rate
        self._expiry[key] = datetime.now() + timedelta(seconds=self.ttl_seconds)

    def clear(self) -> None:
        """Clear all cached rates."""
        self._cache.clear()
        self._expiry.clear()
