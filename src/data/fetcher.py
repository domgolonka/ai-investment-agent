"""
Smart Multi-Source Data Fetcher with Unified Parallel Approach

REFACTORED: Modular structure with orchestration-only main class.

Strategy:
1. Launch ALL sources in parallel (yfinance, yahooquery, FMP, EODHD, Alpha Vantage)
2. Enhance yfinance with financial statement extraction
3. Smart merge with quality scoring (Statements > EODHD > Alpha Vantage/yfinance > FMP > Yahoo Info)
4. Mandatory Tavily gap-fill if coverage <70%

Module Structure:
- base_fetcher.py: BaseFetcher abstract class, constants, DataQuality
- yfinance_fetcher.py: YFinance and YahooQuery fetchers
- source_fetchers.py: FMP, EODHD, Alpha Vantage fetchers
- quality_merger.py: Quality scoring, merging, normalization
- fetcher.py: SmartMarketDataFetcher orchestration (this file)
"""

import asyncio
import pandas as pd
import structlog
from datetime import datetime
from typing import Dict, Any, Optional

from src.exceptions import DataFetchError

# Import from modular components
from src.data.base_fetcher import (
    DataQuality,
    FetcherStats,
    SOURCE_QUALITY,
    PER_SOURCE_TIMEOUT,
)
from src.data.yfinance_fetcher import YFinanceFetcher, YahooQueryFetcher
from src.data.source_fetchers import FMPFetcher, EODHDFetcher, AlphaVantageFetcher
from src.data.quality_merger import (
    QualityMerger,
    DataNormalizer,
    FinancialPatternExtractor,
)

logger = structlog.get_logger(__name__)

# Re-export for backward compatibility
# These were originally defined in this file
__all__ = [
    'SmartMarketDataFetcher',
    'fetcher',
    'fetch_ticker_data',
    'FinancialPatternExtractor',
    'SOURCE_QUALITY',
    'DataQuality',
]


class SmartMarketDataFetcher:
    """
    Intelligent multi-source fetcher with unified parallel approach.

    Orchestrates data fetching from multiple sources:
    - YFinance (with statement extraction)
    - YahooQuery (fallback)
    - FMP (Financial Modeling Prep)
    - EODHD (EOD Historical Data)
    - Alpha Vantage

    Uses quality-based merging to produce the best composite result.
    """

    REQUIRED_BASICS = ['symbol', 'currentPrice', 'currency']

    IMPORTANT_FIELDS = [
        'marketCap', 'trailingPE', 'priceToBook', 'returnOnEquity',
        'revenueGrowth', 'profitMargins', 'operatingMargins', 'grossMargins',
        'debtToEquity', 'currentRatio', 'freeCashflow', 'operatingCashflow',
        'numberOfAnalystOpinions', 'pegRatio', 'forwardPE'
    ]

    def __init__(self):
        # Initialize fetchers
        self.yfinance_fetcher = YFinanceFetcher()
        self.yahooquery_fetcher = YahooQueryFetcher()
        self.fmp_fetcher = FMPFetcher()
        self.eodhd_fetcher = EODHDFetcher()
        self.av_fetcher = AlphaVantageFetcher()

        # Initialize merger and normalizer
        self.quality_merger = QualityMerger()
        self.data_normalizer = DataNormalizer(
            fx_rate_fetcher=self.yfinance_fetcher.get_currency_rate
        )

        # Statistics tracking
        self.stats = FetcherStats()

    async def _fetch_all_sources_parallel(
        self,
        symbol: str
    ) -> Dict[str, Optional[Dict]]:
        """
        PHASE 1: Launch all data sources in parallel.

        Args:
            symbol: Ticker symbol to fetch

        Returns:
            Dictionary mapping source names to their results
        """
        logger.info("launching_parallel_sources", symbol=symbol)

        tasks = {
            'yfinance': self.yfinance_fetcher.fetch(symbol),
            'yahooquery': self.yahooquery_fetcher.fetch(symbol),
            'fmp': self.fmp_fetcher.fetch(symbol),
            'eodhd': self.eodhd_fetcher.fetch(symbol),
            'alpha_vantage': self.av_fetcher.fetch(symbol),
        }

        results = {}
        for source_name, coro in tasks.items():
            try:
                result = await asyncio.wait_for(coro, timeout=PER_SOURCE_TIMEOUT)
                results[source_name] = result

                if result:
                    logger.info(
                        f"{source_name}_success",
                        symbol=symbol,
                        fields=len(result)
                    )
                    self._update_source_stats(source_name)
                else:
                    logger.warning(f"{source_name}_returned_none", symbol=symbol)

            except asyncio.TimeoutError:
                logger.warning(f"{source_name}_timeout", symbol=symbol)
                results[source_name] = None
            except asyncio.CancelledError:
                logger.warning(f"{source_name}_cancelled", symbol=symbol)
                results[source_name] = None
            except (ConnectionError, OSError) as e:
                logger.warning(
                    f"{source_name}_connection_error",
                    symbol=symbol,
                    error_type=type(e).__name__,
                    error=str(e)
                )
                results[source_name] = None
            except Exception as e:
                logger.warning(
                    f"{source_name}_error",
                    symbol=symbol,
                    error_type=type(e).__name__,
                    error=str(e)
                )
                results[source_name] = None

        return results

    def _update_source_stats(self, source_name: str) -> None:
        """Update statistics for a successful source fetch."""
        if source_name in self.stats.sources:
            self.stats.sources[source_name] += 1

    async def get_financial_metrics(
        self,
        ticker: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        UNIFIED APPROACH: Main entry point with parallel sources and mandatory gap-filling.

        Args:
            ticker: The ticker symbol to fetch data for
            timeout: Overall timeout for the operation

        Returns:
            Dictionary containing financial metrics and metadata
        """
        self.stats.fetches += 1
        start_time = datetime.now()

        try:
            # PHASE 1: Parallel source execution
            source_results = await self._fetch_all_sources_parallel(ticker)

            # PHASE 2: Smart merge with quality scoring
            merged, merge_metadata = self.quality_merger.smart_merge_with_quality(
                source_results, ticker
            )

            # Panic Mode for Asian tickers
            merged = await self._handle_panic_mode(
                ticker, merged, merge_metadata
            )

            if not merged:
                return {"error": "No data available", "symbol": ticker}

            # PHASE 3: Calculate coverage and identify gaps
            coverage = self.quality_merger.calculate_coverage(merged)
            gaps = self.quality_merger.identify_critical_gaps(merged)

            # PHASE 4: Mandatory Tavily gap-filling if needed
            if coverage < 0.70 and gaps:
                tavily_data = await self.quality_merger.fetch_tavily_gaps(
                    ticker, gaps
                )
                if tavily_data:
                    merged = self.quality_merger.merge_gap_fill_data(
                        merged, tavily_data, merge_metadata
                    )

            # PHASE 5: Derived metrics and normalization
            calculated = self.quality_merger.calculate_derived_metrics(
                merged, ticker
            )
            if calculated:
                result = self.quality_merger.merge_data(merged, calculated)
                merged = result.data
                merge_metadata['gaps_filled'] += result.gaps_filled

            merged = self.data_normalizer.normalize_data_integrity(merged, ticker)

            # PHASE 6: Validation and metadata
            quality = self.quality_merger.validate_basics(
                merged, ticker, merge_metadata.get('sources_used', [])
            )

            if quality.basics_ok:
                self.stats.basics_ok += 1
            else:
                self.stats.basics_failed += 1

            # Add metadata to result
            merged.update({
                '_coverage_pct': coverage,
                '_data_source': merge_metadata['composite_source'],
                '_sources_used': merge_metadata['sources_used'],
                '_gaps_filled': merge_metadata['gaps_filled'],
                '_quality': {
                    'basics_ok': quality.basics_ok,
                    'coverage_pct': quality.coverage_pct,
                    'sources_used': quality.sources_used,
                }
            })

            return merged

        except asyncio.CancelledError:
            logger.warning("fetch_cancelled", ticker=ticker)
            raise

        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(
                "fetch_network_error",
                ticker=ticker,
                error_type=type(e).__name__,
                error=str(e)
            )
            raise DataFetchError(
                f"Network error fetching data for {ticker}",
                source="multi_source_fetcher",
                ticker=ticker,
                cause=e
            )

        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "fetch_data_processing_error",
                ticker=ticker,
                error_type=type(e).__name__,
                error=str(e)
            )
            return {"error": str(e), "symbol": ticker}

        except Exception as e:
            logger.error(
                "unexpected_fetch_error",
                ticker=ticker,
                error_type=type(e).__name__,
                error=str(e)
            )
            return {"error": str(e), "symbol": ticker}

    async def _handle_panic_mode(
        self,
        ticker: str,
        merged: Dict[str, Any],
        merge_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle panic mode for Asian tickers or empty results.

        Triggers aggressive Tavily search when standard sources fail.
        """
        basics_failed = not all(
            k in merged for k in self.REQUIRED_BASICS
        )
        is_asian = ticker.endswith(('.HK', '.TW', '.KS', '.T'))

        if not merged or (is_asian and basics_failed):
            logger.warning(
                "data_vacuum_detected",
                symbol=ticker,
                msg="Triggering Panic Mode for Asian ticker"
            )
            all_critical = self.IMPORTANT_FIELDS + self.REQUIRED_BASICS
            tavily_rescue = await self.quality_merger.fetch_tavily_gaps(
                ticker, all_critical
            )

            if tavily_rescue:
                merged = self.quality_merger.merge_gap_fill_data(
                    merged, tavily_rescue, merge_metadata
                )
                if 'currentPrice' not in merged and 'price' in tavily_rescue:
                    merged['currentPrice'] = tavily_rescue['price']

        return merged

    async def get_historical_prices(
        self,
        ticker: str,
        period: str = "1y"
    ) -> pd.DataFrame:
        """
        Fetch historical price data.

        Args:
            ticker: Ticker symbol
            period: Time period (e.g., "1y", "6mo", "3mo")

        Returns:
            DataFrame with historical price data
        """
        return await self.yfinance_fetcher.get_historical_prices(ticker, period)

    def get_currency_rate(self, from_curr: str, to_curr: str) -> float:
        """
        Get FX rate with caching.

        Args:
            from_curr: Source currency code
            to_curr: Target currency code

        Returns:
            Exchange rate
        """
        return self.yfinance_fetcher.get_currency_rate(from_curr, to_curr)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics on fetcher performance."""
        return self.stats.copy()

    def clear_fx_cache(self) -> None:
        """Clear FX rate cache."""
        self.yfinance_fetcher.fx_cache.clear()


# Singleton instance
fetcher = SmartMarketDataFetcher()


# Backward compatibility function
async def fetch_ticker_data(ticker: str) -> Dict[str, Any]:
    """
    Backward compatible function for fetching ticker data.

    Args:
        ticker: The ticker symbol to fetch

    Returns:
        Dictionary containing financial metrics
    """
    return await fetcher.get_financial_metrics(ticker)
