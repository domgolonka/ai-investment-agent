"""
Data Fetching Module

Provides multi-source financial data fetching with quality-based merging.

Module Structure:
- base_fetcher.py: BaseFetcher abstract class, constants, DataQuality
- yfinance_fetcher.py: YFinance and YahooQuery fetchers
- source_fetchers.py: FMP, EODHD, Alpha Vantage fetchers
- quality_merger.py: Quality scoring, merging, normalization
- fetcher.py: SmartMarketDataFetcher orchestration

Usage:
    from src.data import fetcher, fetch_ticker_data
    from src.data.fetcher import SmartMarketDataFetcher

    # Using the singleton instance
    data = await fetcher.get_financial_metrics("AAPL")

    # Using the convenience function
    data = await fetch_ticker_data("AAPL")

    # Creating a new instance
    my_fetcher = SmartMarketDataFetcher()
    data = await my_fetcher.get_financial_metrics("AAPL")
"""

# Main exports from fetcher.py (backward compatibility)
from src.data.fetcher import (
    SmartMarketDataFetcher,
    fetcher,
    fetch_ticker_data,
)

# Base classes and utilities
from src.data.base_fetcher import (
    BaseFetcher,
    DataQuality,
    FetcherStats,
    FXRateCache,
    SOURCE_QUALITY,
    MIN_INFO_FIELDS,
    PER_SOURCE_TIMEOUT,
    FX_CACHE_TTL_SECONDS,
    ROE_PERCENTAGE_THRESHOLD,
    DEBT_EQUITY_PERCENTAGE_THRESHOLD,
)

# Individual fetchers
from src.data.yfinance_fetcher import (
    YFinanceFetcher,
    YahooQueryFetcher,
)

from src.data.source_fetchers import (
    FMPFetcher,
    EODHDFetcher,
    AlphaVantageFetcher,
    get_available_sources,
)

# Quality and merging
from src.data.quality_merger import (
    QualityMerger,
    DataNormalizer,
    FinancialPatternExtractor,
    MergeResult,
)

__all__ = [
    # Main class and singleton
    'SmartMarketDataFetcher',
    'fetcher',
    'fetch_ticker_data',

    # Base classes
    'BaseFetcher',
    'DataQuality',
    'FetcherStats',
    'FXRateCache',

    # Individual fetchers
    'YFinanceFetcher',
    'YahooQueryFetcher',
    'FMPFetcher',
    'EODHDFetcher',
    'AlphaVantageFetcher',

    # Quality and merging
    'QualityMerger',
    'DataNormalizer',
    'FinancialPatternExtractor',
    'MergeResult',

    # Utilities
    'get_available_sources',

    # Constants
    'SOURCE_QUALITY',
    'MIN_INFO_FIELDS',
    'PER_SOURCE_TIMEOUT',
    'FX_CACHE_TTL_SECONDS',
    'ROE_PERCENTAGE_THRESHOLD',
    'DEBT_EQUITY_PERCENTAGE_THRESHOLD',
]
