"""
PeerMetrics - Fetch and aggregate metrics for peer group analysis.

This module provides utilities for fetching financial metrics from multiple
tickers and calculating peer group statistics (median, average, percentiles).
"""

import yfinance as yf
import structlog
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from src.exceptions import DataFetchError, DataValidationError

logger = structlog.get_logger(__name__)


@dataclass
class TickerMetrics:
    """Financial metrics for a single ticker."""

    ticker: str
    # Valuation metrics
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    peg_ratio: Optional[float] = None

    # Growth metrics
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    earnings_growth_yoy: Optional[float] = None

    # Profitability metrics
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    gross_margin: Optional[float] = None
    roe: Optional[float] = None  # Return on Equity
    roa: Optional[float] = None  # Return on Assets
    roic: Optional[float] = None  # Return on Invested Capital

    # Financial health metrics
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    total_cash: Optional[float] = None
    total_debt: Optional[float] = None
    free_cash_flow: Optional[float] = None

    # Other useful metrics
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    beta: Optional[float] = None
    dividend_yield: Optional[float] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "yfinance"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {
            k: v for k, v in self.__dict__.items()
            if v is not None and k not in ["timestamp", "source"]
        }

    def get_metric(self, metric_name: str) -> Optional[float]:
        """Safely get a metric value by name."""
        return getattr(self, metric_name, None)


@dataclass
class PeerGroupStats:
    """Aggregated statistics for a peer group."""

    metric_name: str
    values: List[float]
    median: float
    mean: float
    std_dev: float
    min_value: float
    max_value: float
    percentile_25: float
    percentile_75: float
    count: int

    def get_percentile(self, value: float) -> float:
        """Calculate percentile rank of a value in the peer group."""
        if not self.values or value is None:
            return 0.0
        return float(np.percentile(self.values, 50)) if len(self.values) == 1 else \
               float((sum(v < value for v in self.values) / len(self.values)) * 100)

    def is_outlier(self, value: float, std_threshold: float = 2.0) -> bool:
        """Check if a value is an outlier (beyond N standard deviations)."""
        if value is None or self.std_dev == 0:
            return False
        z_score = abs((value - self.mean) / self.std_dev)
        return z_score > std_threshold


class PeerMetrics:
    """
    Fetch and aggregate financial metrics for peer group analysis.

    Features:
    - Concurrent fetching of metrics for multiple tickers
    - Comprehensive metric extraction from yfinance
    - Statistical aggregation (median, mean, percentiles)
    - Percentile ranking calculations
    - Outlier detection

    Example:
        metrics_helper = PeerMetrics()

        # Fetch metrics for multiple tickers
        metrics = await metrics_helper.get_peer_metrics(["AAPL", "MSFT", "GOOGL"])

        # Calculate peer statistics
        pe_stats = metrics_helper.calculate_metric_stats(metrics, "pe_ratio")

        # Get percentile rank
        aapl_percentile = metrics_helper.calculate_percentile(
            metrics["AAPL"].pe_ratio,
            [m.pe_ratio for m in metrics.values()]
        )
    """

    def __init__(self, fetch_timeout: int = 15, max_concurrent: int = 10):
        """
        Initialize PeerMetrics.

        Args:
            fetch_timeout: Timeout for fetching individual ticker data (seconds)
            max_concurrent: Maximum concurrent API requests
        """
        self._fetch_timeout = fetch_timeout
        self._max_concurrent = max_concurrent
        logger.info(
            "peer_metrics_initialized",
            timeout=fetch_timeout,
            max_concurrent=max_concurrent,
        )

    async def get_peer_metrics(
        self, tickers: List[str], include_focus: bool = True
    ) -> Dict[str, TickerMetrics]:
        """
        Fetch financial metrics for a list of tickers.

        Args:
            tickers: List of ticker symbols
            include_focus: Whether to include first ticker (focus ticker)

        Returns:
            Dict mapping ticker to TickerMetrics

        Raises:
            DataFetchError: If fetching fails for all tickers
        """
        if not tickers:
            return {}

        logger.info("fetching_peer_metrics", ticker_count=len(tickers))

        semaphore = asyncio.Semaphore(self._max_concurrent)
        results = {}

        async def fetch_with_semaphore(ticker: str):
            async with semaphore:
                try:
                    metrics = await asyncio.wait_for(
                        self._fetch_ticker_metrics(ticker),
                        timeout=self._fetch_timeout,
                    )
                    return ticker, metrics
                except asyncio.TimeoutError:
                    logger.warning("fetch_timeout", ticker=ticker)
                    return ticker, None
                except Exception as e:
                    logger.warning("fetch_failed", ticker=ticker, error=str(e))
                    return ticker, None

        # Execute all fetches concurrently
        tasks = [fetch_with_semaphore(t) for t in tickers]
        fetch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in fetch_results:
            if isinstance(result, Exception):
                logger.error("fetch_exception", error=str(result))
                continue
            ticker, metrics = result
            if metrics:
                results[ticker] = metrics

        success_count = len(results)
        logger.info(
            "peer_metrics_fetched",
            total=len(tickers),
            success=success_count,
            failed=len(tickers) - success_count,
        )

        if not results:
            raise DataFetchError(
                "Failed to fetch metrics for all tickers",
                details={"tickers": tickers},
            )

        return results

    async def _fetch_ticker_metrics(self, ticker: str) -> TickerMetrics:
        """
        Fetch comprehensive metrics for a single ticker.

        Args:
            ticker: Ticker symbol

        Returns:
            TickerMetrics object

        Raises:
            DataFetchError: If fetching fails
        """
        try:
            stock = yf.Ticker(ticker)
            info = await asyncio.to_thread(lambda: stock.info)

            if not info or "symbol" not in info:
                raise DataFetchError(
                    f"No data returned for {ticker}",
                    ticker=ticker,
                    source="yfinance",
                )

            # Extract metrics with safe fallbacks
            metrics = TickerMetrics(
                ticker=ticker,
                # Valuation
                pe_ratio=self._safe_float(info.get("trailingPE")),
                forward_pe=self._safe_float(info.get("forwardPE")),
                pb_ratio=self._safe_float(info.get("priceToBook")),
                ps_ratio=self._safe_float(info.get("priceToSalesTrailing12Months")),
                ev_ebitda=self._safe_float(info.get("enterpriseToEbitda")),
                peg_ratio=self._safe_float(info.get("pegRatio")),
                # Growth
                revenue_growth=self._safe_float(info.get("revenueGrowth")),
                earnings_growth=self._safe_float(info.get("earningsGrowth")),
                revenue_growth_yoy=self._safe_float(info.get("revenueQuarterlyGrowth")),
                earnings_growth_yoy=self._safe_float(info.get("earningsQuarterlyGrowth")),
                # Profitability
                profit_margin=self._safe_float(info.get("profitMargins")),
                operating_margin=self._safe_float(info.get("operatingMargins")),
                gross_margin=self._safe_float(info.get("grossMargins")),
                roe=self._safe_float(info.get("returnOnEquity")),
                roa=self._safe_float(info.get("returnOnAssets")),
                roic=self._safe_float(info.get("returnOnCapital")),
                # Financial Health
                debt_to_equity=self._safe_float(info.get("debtToEquity")),
                current_ratio=self._safe_float(info.get("currentRatio")),
                quick_ratio=self._safe_float(info.get("quickRatio")),
                total_cash=self._safe_float(info.get("totalCash")),
                total_debt=self._safe_float(info.get("totalDebt")),
                free_cash_flow=self._safe_float(info.get("freeCashflow")),
                # Other
                market_cap=self._safe_float(info.get("marketCap")),
                enterprise_value=self._safe_float(info.get("enterpriseValue")),
                beta=self._safe_float(info.get("beta")),
                dividend_yield=self._safe_float(info.get("dividendYield")),
            )

            logger.debug("ticker_metrics_fetched", ticker=ticker)
            return metrics

        except Exception as e:
            if isinstance(e, DataFetchError):
                raise
            raise DataFetchError(
                f"Failed to fetch metrics for {ticker}",
                ticker=ticker,
                source="yfinance",
                cause=e,
            )

    def calculate_metric_stats(
        self, metrics: Dict[str, TickerMetrics], metric_name: str
    ) -> Optional[PeerGroupStats]:
        """
        Calculate statistics for a specific metric across peer group.

        Args:
            metrics: Dict of ticker to TickerMetrics
            metric_name: Name of metric to analyze (e.g., "pe_ratio")

        Returns:
            PeerGroupStats object or None if insufficient data
        """
        # Extract metric values
        values = []
        for ticker_metrics in metrics.values():
            value = ticker_metrics.get_metric(metric_name)
            if value is not None and not np.isnan(value) and np.isfinite(value):
                values.append(float(value))

        if len(values) < 2:
            logger.warning(
                "insufficient_data_for_stats",
                metric=metric_name,
                count=len(values),
            )
            return None

        values_array = np.array(values)

        stats = PeerGroupStats(
            metric_name=metric_name,
            values=values,
            median=float(np.median(values_array)),
            mean=float(np.mean(values_array)),
            std_dev=float(np.std(values_array)),
            min_value=float(np.min(values_array)),
            max_value=float(np.max(values_array)),
            percentile_25=float(np.percentile(values_array, 25)),
            percentile_75=float(np.percentile(values_array, 75)),
            count=len(values),
        )

        logger.debug(
            "metric_stats_calculated",
            metric=metric_name,
            count=stats.count,
            median=stats.median,
            mean=stats.mean,
        )

        return stats

    def calculate_peer_median(
        self, metrics: Dict[str, TickerMetrics]
    ) -> Dict[str, float]:
        """
        Calculate median for all metrics across peer group.

        Args:
            metrics: Dict of ticker to TickerMetrics

        Returns:
            Dict mapping metric name to median value
        """
        if not metrics:
            return {}

        # Get all metric names from first ticker
        sample_metrics = next(iter(metrics.values()))
        metric_names = [
            k for k in sample_metrics.__dict__.keys()
            if k not in ["ticker", "timestamp", "source"]
        ]

        medians = {}
        for metric_name in metric_names:
            stats = self.calculate_metric_stats(metrics, metric_name)
            if stats:
                medians[metric_name] = stats.median

        return medians

    def calculate_peer_average(
        self, metrics: Dict[str, TickerMetrics]
    ) -> Dict[str, float]:
        """
        Calculate average for all metrics across peer group.

        Args:
            metrics: Dict of ticker to TickerMetrics

        Returns:
            Dict mapping metric name to average value
        """
        if not metrics:
            return {}

        # Get all metric names from first ticker
        sample_metrics = next(iter(metrics.values()))
        metric_names = [
            k for k in sample_metrics.__dict__.keys()
            if k not in ["ticker", "timestamp", "source"]
        ]

        averages = {}
        for metric_name in metric_names:
            stats = self.calculate_metric_stats(metrics, metric_name)
            if stats:
                averages[metric_name] = stats.mean

        return averages

    def calculate_percentile(
        self, ticker_value: Optional[float], peer_values: List[Optional[float]]
    ) -> float:
        """
        Calculate percentile rank of a ticker's value within peer group.

        Args:
            ticker_value: The value to rank
            peer_values: List of peer values (may contain None)

        Returns:
            Percentile rank (0-100), or 0 if insufficient data

        Example:
            A percentile of 80 means the ticker is better than 80% of peers
            (assuming higher is better for the metric)
        """
        if ticker_value is None:
            return 0.0

        # Filter out None values and ensure valid floats
        valid_values = [
            float(v) for v in peer_values
            if v is not None and not np.isnan(v) and np.isfinite(v)
        ]

        if len(valid_values) < 2:
            return 50.0  # Default to median if insufficient data

        # Add ticker value to the list for percentile calculation
        all_values = valid_values + [float(ticker_value)]

        # Calculate percentile using numpy
        percentile = (
            sum(v < ticker_value for v in valid_values) / len(valid_values)
        ) * 100

        return round(percentile, 2)

    def get_metric_ranking(
        self,
        metrics: Dict[str, TickerMetrics],
        metric_name: str,
        ascending: bool = False,
    ) -> List[Tuple[str, float]]:
        """
        Get ranked list of tickers by a specific metric.

        Args:
            metrics: Dict of ticker to TickerMetrics
            metric_name: Name of metric to rank by
            ascending: If True, rank from low to high; if False, high to low

        Returns:
            List of (ticker, value) tuples in ranked order
        """
        # Extract metric values
        ticker_values = []
        for ticker, ticker_metrics in metrics.items():
            value = ticker_metrics.get_metric(metric_name)
            if value is not None and not np.isnan(value) and np.isfinite(value):
                ticker_values.append((ticker, float(value)))

        # Sort by value
        ticker_values.sort(key=lambda x: x[1], reverse=not ascending)

        return ticker_values

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Safely convert value to float, returning None for invalid values."""
        if value is None:
            return None
        try:
            f_value = float(value)
            # Check for NaN or infinity
            if np.isnan(f_value) or np.isinf(f_value):
                return None
            return f_value
        except (ValueError, TypeError):
            return None

    def get_coverage_report(
        self, metrics: Dict[str, TickerMetrics]
    ) -> Dict[str, Any]:
        """
        Generate a report on data coverage across metrics.

        Args:
            metrics: Dict of ticker to TickerMetrics

        Returns:
            Coverage statistics
        """
        if not metrics:
            return {"total_tickers": 0, "metrics": {}}

        # Get all metric names
        sample_metrics = next(iter(metrics.values()))
        metric_names = [
            k for k in sample_metrics.__dict__.keys()
            if k not in ["ticker", "timestamp", "source"]
        ]

        total_tickers = len(metrics)
        coverage = {}

        for metric_name in metric_names:
            count = sum(
                1 for m in metrics.values()
                if m.get_metric(metric_name) is not None
            )
            coverage[metric_name] = {
                "available": count,
                "missing": total_tickers - count,
                "coverage_pct": round((count / total_tickers) * 100, 2),
            }

        return {
            "total_tickers": total_tickers,
            "metrics": coverage,
        }
