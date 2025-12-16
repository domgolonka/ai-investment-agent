"""
External Source Fetchers

FMP, EODHD, and Alpha Vantage data fetchers with circuit breaker support.
"""

import asyncio
import structlog
from typing import Dict, Any, Optional

from src.data.base_fetcher import BaseFetcher

logger = structlog.get_logger(__name__)

# Optional dependency imports
try:
    from src.data.fmp_fetcher import get_fmp_fetcher
    FMP_AVAILABLE = True
except ImportError:
    FMP_AVAILABLE = False
    logger.warning("fmp_not_available")

try:
    from src.data.eodhd_fetcher import get_eodhd_fetcher
    EODHD_AVAILABLE = True
except ImportError:
    EODHD_AVAILABLE = False
    logger.warning("eodhd_not_available")

try:
    from src.data.alpha_vantage_fetcher import get_av_fetcher
    ALPHA_VANTAGE_AVAILABLE = True
except ImportError:
    ALPHA_VANTAGE_AVAILABLE = False
    logger.warning("alpha_vantage_not_available")


class FMPFetcher(BaseFetcher):
    """
    Financial Modeling Prep (FMP) data fetcher.

    Good backup source for fundamental data.
    """

    # Key mapping from FMP to yfinance-style fields
    KEY_MAPPING = {
        'pe': 'trailingPE',
        'pb': 'priceToBook',
        'peg': 'pegRatio',
        'roe': 'returnOnEquity',
        'marketCap': 'marketCap',
        'revenue_growth': 'revenueGrowth',
        'debt_to_equity': 'debtToEquity'
    }

    def __init__(self, timeout: int = 15):
        super().__init__(timeout)
        self._fetcher = get_fmp_fetcher() if FMP_AVAILABLE else None

    async def fetch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from FMP."""
        if not self.is_available():
            return None

        try:
            fmp_data = await self._fetcher.get_financial_metrics(symbol)

            if not fmp_data:
                return None

            # Check if data has any non-null values (excluding _source)
            if all(v is None for k, v in fmp_data.items() if k != '_source'):
                return None

            return self._map_keys(fmp_data)

        except (KeyError, TypeError) as e:
            logger.debug(
                "fmp_data_mapping_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "fmp_network_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.warning(
                "fmp_fallback_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate FMP data."""
        if not data:
            return False
        # Check for at least one meaningful value
        return any(v is not None for k, v in data.items() if not k.startswith('_'))

    def is_available(self) -> bool:
        """Check if FMP fetcher is available."""
        return (
            FMP_AVAILABLE and
            self._fetcher is not None and
            self._fetcher.is_available()
        )

    def _map_keys(self, fmp_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map FMP keys to yfinance-style keys."""
        mapped = {}
        for fmp_key, yf_key in self.KEY_MAPPING.items():
            if fmp_data.get(fmp_key):
                mapped[yf_key] = fmp_data[fmp_key]
        return mapped


class EODHDFetcher(BaseFetcher):
    """
    EOD Historical Data (EODHD) fetcher.

    Professional paid feed, high quality for international coverage.
    Includes circuit breaker for rate limit handling.
    """

    def __init__(self, timeout: int = 15):
        super().__init__(timeout)
        self._fetcher = get_eodhd_fetcher() if EODHD_AVAILABLE else None

    async def fetch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from EODHD.

        Gracefully handles API limits/errors by returning None.
        """
        if not self.is_available():
            return None

        try:
            data = await self._fetcher.get_financial_metrics(symbol)

            # If successful and contains data
            if data and any(v is not None for k, v in data.items() if k != '_source'):
                return data

            return None

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "eodhd_network_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except (KeyError, TypeError, ValueError) as e:
            logger.debug(
                "eodhd_data_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.warning(
                "eodhd_fetch_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate EODHD data."""
        if not data:
            return False
        return any(v is not None for k, v in data.items() if k != '_source')

    def is_available(self) -> bool:
        """Check if EODHD fetcher is available (including circuit breaker)."""
        if not EODHD_AVAILABLE or not self._fetcher:
            return False
        return self._fetcher.is_available()


class AlphaVantageFetcher(BaseFetcher):
    """
    Alpha Vantage data fetcher.

    High-quality fundamentals with circuit breaker for rate limit handling.
    Free tier: 25 requests/day, 5 requests/minute.
    """

    def __init__(self, timeout: int = 15):
        super().__init__(timeout)
        self._fetcher = get_av_fetcher() if ALPHA_VANTAGE_AVAILABLE else None

    async def fetch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from Alpha Vantage.

        Includes circuit breaker for rate limit handling.
        """
        if not self.is_available():
            return None

        try:
            data = await self._fetcher.get_financial_metrics(symbol)

            # If successful and contains data
            if data and any(v is not None for k, v in data.items() if not k.startswith('_')):
                return data

            return None

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "alpha_vantage_network_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except (KeyError, TypeError, ValueError) as e:
            logger.debug(
                "alpha_vantage_data_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.warning(
                "alpha_vantage_fetch_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate Alpha Vantage data."""
        if not data:
            return False
        return any(v is not None for k, v in data.items() if not k.startswith('_'))

    def is_available(self) -> bool:
        """Check if Alpha Vantage fetcher is available (including circuit breaker)."""
        if not ALPHA_VANTAGE_AVAILABLE or not self._fetcher:
            return False
        return self._fetcher.is_available()


def get_available_sources() -> Dict[str, bool]:
    """
    Get availability status of all external sources.

    Returns:
        Dictionary mapping source names to availability status
    """
    return {
        'fmp': FMP_AVAILABLE,
        'eodhd': EODHD_AVAILABLE,
        'alpha_vantage': ALPHA_VANTAGE_AVAILABLE,
    }
