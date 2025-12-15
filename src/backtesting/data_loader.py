"""
Historical data loader for backtesting.

This module provides functionality to load and cache historical price data
from various sources (primarily yfinance) for backtesting purposes.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import yfinance as yf

from src.exceptions import DataFetchError, DataValidationError

logger = logging.getLogger(__name__)


@dataclass
class DataLoaderConfig:
    """Configuration for the historical data loader."""

    cache_dir: Path = field(default_factory=lambda: Path("data/backtest_cache"))
    cache_enabled: bool = True
    auto_adjust: bool = True  # Adjust for splits and dividends
    validate_data: bool = True
    min_data_points: int = 20  # Minimum required data points


class HistoricalDataLoader:
    """
    Loads and caches historical price data for backtesting.

    This class handles fetching historical stock data from yfinance,
    caching it locally to avoid repeated API calls, and validating
    data quality before use.

    Attributes:
        config: Configuration for data loading and caching
        _cache: In-memory cache of loaded data

    Example:
        >>> loader = HistoricalDataLoader()
        >>> data = loader.load_price_data(
        ...     ticker="AAPL",
        ...     start_date="2023-01-01",
        ...     end_date="2024-01-01"
        ... )
        >>> print(data.head())
    """

    def __init__(self, config: Optional[DataLoaderConfig] = None):
        """
        Initialize the historical data loader.

        Args:
            config: Optional configuration, uses defaults if not provided
        """
        self.config = config or DataLoaderConfig()
        self._cache: Dict[str, pd.DataFrame] = {}

        # Create cache directory if it doesn't exist
        if self.config.cache_enabled:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"HistoricalDataLoader initialized (cache_enabled={self.config.cache_enabled})"
        )

    def load_price_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Load historical price data for a ticker.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            interval: Data interval (1d, 1h, etc.)

        Returns:
            DataFrame with OHLCV data indexed by date

        Raises:
            DataFetchError: If data cannot be fetched
            DataValidationError: If data validation fails
        """
        cache_key = self._get_cache_key(ticker, start_date, end_date, interval)

        # Check in-memory cache first
        if cache_key in self._cache:
            logger.debug(f"Loading {ticker} from memory cache")
            return self._cache[cache_key].copy()

        # Check file cache
        if self.config.cache_enabled:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                logger.debug(f"Loading {ticker} from file cache")
                self._cache[cache_key] = cached_data
                return cached_data.copy()

        # Fetch from API
        logger.info(f"Fetching {ticker} data from {start_date} to {end_date}")
        try:
            data = self._fetch_from_yfinance(ticker, start_date, end_date, interval)
        except Exception as e:
            raise DataFetchError(
                f"Failed to fetch data for {ticker}",
                source="yfinance",
                ticker=ticker,
                cause=e,
            ) from e

        # Validate data
        if self.config.validate_data:
            self._validate_data(data, ticker, start_date, end_date)

        # Cache the data
        if self.config.cache_enabled:
            self._save_to_cache(cache_key, data)

        self._cache[cache_key] = data
        return data.copy()

    def load_benchmark_data(
        self,
        benchmark: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Load benchmark data for comparison (e.g., SPY, QQQ).

        Args:
            benchmark: Benchmark ticker symbol (e.g., 'SPY')
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)

        Returns:
            DataFrame with benchmark price data

        Raises:
            DataFetchError: If benchmark data cannot be fetched
        """
        logger.info(f"Loading benchmark data: {benchmark}")
        return self.load_price_data(
            ticker=benchmark,
            start_date=start_date,
            end_date=end_date,
        )

    def resample_data(
        self,
        data: pd.DataFrame,
        frequency: str,
    ) -> pd.DataFrame:
        """
        Resample data to a different timeframe.

        Args:
            data: Original OHLCV data
            frequency: Target frequency ('W' for weekly, 'M' for monthly, etc.)

        Returns:
            Resampled DataFrame

        Example:
            >>> daily_data = loader.load_price_data("AAPL", "2023-01-01", "2024-01-01")
            >>> weekly_data = loader.resample_data(daily_data, 'W')
        """
        logger.debug(f"Resampling data to {frequency} frequency")

        resampled = data.resample(frequency).agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )

        # Drop rows with NaN values
        resampled = resampled.dropna()

        return resampled

    def clear_cache(self, ticker: Optional[str] = None) -> None:
        """
        Clear cached data.

        Args:
            ticker: If provided, only clear cache for this ticker.
                   Otherwise, clear all cache.
        """
        if ticker:
            # Clear specific ticker from memory cache
            keys_to_remove = [k for k in self._cache.keys() if ticker in k]
            for key in keys_to_remove:
                del self._cache[key]

            # Clear from file cache
            if self.config.cache_enabled:
                for cache_file in self.config.cache_dir.glob(f"*{ticker}*.parquet"):
                    cache_file.unlink()
                    logger.debug(f"Removed cache file: {cache_file}")
        else:
            # Clear all caches
            self._cache.clear()
            if self.config.cache_enabled:
                for cache_file in self.config.cache_dir.glob("*.parquet"):
                    cache_file.unlink()
            logger.info("Cleared all cached data")

    def _fetch_from_yfinance(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str,
    ) -> pd.DataFrame:
        """Fetch data from yfinance API."""
        stock = yf.Ticker(ticker)
        data = stock.history(
            start=start_date,
            end=end_date,
            interval=interval,
            auto_adjust=self.config.auto_adjust,
        )

        if data.empty:
            raise DataFetchError(
                f"No data returned for {ticker}",
                source="yfinance",
                ticker=ticker,
            )

        # Ensure consistent column names
        data.columns = data.columns.str.title()

        return data

    def _validate_data(
        self,
        data: pd.DataFrame,
        ticker: str,
        start_date: str,
        end_date: str,
    ) -> None:
        """Validate fetched data for quality and completeness."""
        # Check if we have minimum data points
        if len(data) < self.config.min_data_points:
            raise DataValidationError(
                f"Insufficient data points for {ticker}",
                field="data_length",
                value=len(data),
                expected=f"at least {self.config.min_data_points}",
            )

        # Check for required columns
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise DataValidationError(
                f"Missing required columns for {ticker}",
                field="columns",
                value=missing_columns,
                expected=str(required_columns),
            )

        # Check for invalid prices (negative or zero)
        for col in ["Open", "High", "Low", "Close"]:
            if (data[col] <= 0).any():
                raise DataValidationError(
                    f"Invalid {col} prices detected for {ticker}",
                    field=col,
                    value="negative or zero values",
                    expected="positive values",
                )

        # Check for OHLC relationship validity
        invalid_ohlc = (
            (data["High"] < data["Low"])
            | (data["High"] < data["Open"])
            | (data["High"] < data["Close"])
            | (data["Low"] > data["Open"])
            | (data["Low"] > data["Close"])
        )
        if invalid_ohlc.any():
            raise DataValidationError(
                f"Invalid OHLC relationships detected for {ticker}",
                field="OHLC",
                value=f"{invalid_ohlc.sum()} invalid rows",
                expected="High >= Low, High >= Open/Close, Low <= Open/Close",
            )

        logger.debug(f"Data validation passed for {ticker} ({len(data)} rows)")

    def _get_cache_key(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str,
    ) -> str:
        """Generate a unique cache key."""
        return f"{ticker}_{start_date}_{end_date}_{interval}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.config.cache_dir / f"{cache_key}.parquet"

    def _load_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Load data from file cache."""
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            data = pd.read_parquet(cache_path)
            logger.debug(f"Loaded from cache: {cache_path}")
            return data
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_path}: {e}")
            return None

    def _save_to_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """Save data to file cache."""
        cache_path = self._get_cache_path(cache_key)

        try:
            data.to_parquet(cache_path)
            logger.debug(f"Saved to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save cache {cache_path}: {e}")

    def get_date_range(
        self,
        data: pd.DataFrame,
    ) -> Tuple[datetime, datetime]:
        """
        Get the date range of the data.

        Args:
            data: DataFrame with datetime index

        Returns:
            Tuple of (start_date, end_date)
        """
        return data.index.min().to_pydatetime(), data.index.max().to_pydatetime()

    def align_data(
        self,
        data1: pd.DataFrame,
        data2: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Align two DataFrames to have the same date index.

        This is useful for comparing strategy returns with benchmark returns.

        Args:
            data1: First DataFrame
            data2: Second DataFrame

        Returns:
            Tuple of aligned DataFrames
        """
        # Find common date range
        common_dates = data1.index.intersection(data2.index)

        if len(common_dates) == 0:
            raise DataValidationError(
                "No overlapping dates between datasets",
                field="date_range",
                value="no overlap",
                expected="overlapping dates",
            )

        aligned_data1 = data1.loc[common_dates]
        aligned_data2 = data2.loc[common_dates]

        logger.debug(f"Aligned data to {len(common_dates)} common dates")

        return aligned_data1, aligned_data2
