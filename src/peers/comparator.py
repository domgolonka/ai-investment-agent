"""
PeerComparator - Compare companies across valuation, growth, profitability, and financial health.

This module provides comprehensive peer comparison functionality with ranking
and relative analysis capabilities.
"""

import structlog
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.peers.metrics import PeerMetrics, TickerMetrics, PeerGroupStats
from src.peers.finder import PeerFinder
from src.exceptions import DataFetchError, DataValidationError

logger = structlog.get_logger(__name__)


class MetricCategory(Enum):
    """Categories of financial metrics for comparison."""

    VALUATION = "valuation"
    GROWTH = "growth"
    PROFITABILITY = "profitability"
    FINANCIAL_HEALTH = "financial_health"
    EFFICIENCY = "efficiency"


@dataclass
class MetricComparison:
    """Comparison result for a single metric."""

    metric_name: str
    ticker_value: Optional[float]
    peer_median: float
    peer_average: float
    peer_min: float
    peer_max: float
    percentile_rank: float  # 0-100
    vs_median_pct: Optional[float]  # % difference from median
    vs_average_pct: Optional[float]  # % difference from average
    is_outlier: bool = False
    ranking: Optional[int] = None  # 1 = best
    total_ranked: Optional[int] = None

    def is_better_than_median(self, higher_is_better: bool = True) -> bool:
        """Check if ticker value is better than peer median."""
        if self.ticker_value is None:
            return False
        if higher_is_better:
            return self.ticker_value > self.peer_median
        else:
            return self.ticker_value < self.peer_median

    def get_relative_strength(self) -> str:
        """Get relative strength category."""
        if self.percentile_rank >= 75:
            return "Strong"
        elif self.percentile_rank >= 50:
            return "Above Average"
        elif self.percentile_rank >= 25:
            return "Below Average"
        else:
            return "Weak"


@dataclass
class CategoryComparison:
    """Comparison results for a category of metrics."""

    category: MetricCategory
    metrics: Dict[str, MetricComparison]
    overall_score: float  # 0-100, average percentile across metrics
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def get_summary(self) -> str:
        """Get text summary of category comparison."""
        strength_str = f"{len(self.strengths)} strengths" if self.strengths else "no strengths"
        weakness_str = f"{len(self.weaknesses)} weaknesses" if self.weaknesses else "no weaknesses"
        return f"{self.category.value.title()}: Score {self.overall_score:.1f}/100 ({strength_str}, {weakness_str})"


@dataclass
class PeerComparisonResult:
    """Complete peer comparison result."""

    ticker: str
    peers: List[str]
    valuation: Optional[CategoryComparison] = None
    growth: Optional[CategoryComparison] = None
    profitability: Optional[CategoryComparison] = None
    financial_health: Optional[CategoryComparison] = None
    overall_score: Optional[float] = None  # Weighted average
    overall_ranking: Optional[int] = None

    def get_category_scores(self) -> Dict[str, float]:
        """Get scores for all categories."""
        scores = {}
        if self.valuation:
            scores["valuation"] = self.valuation.overall_score
        if self.growth:
            scores["growth"] = self.growth.overall_score
        if self.profitability:
            scores["profitability"] = self.profitability.overall_score
        if self.financial_health:
            scores["financial_health"] = self.financial_health.overall_score
        return scores


class PeerComparator:
    """
    Compare companies across multiple financial dimensions.

    Features:
    - Valuation comparison (P/E, P/B, EV/EBITDA, etc.)
    - Growth comparison (revenue, earnings growth)
    - Profitability comparison (margins, ROE, ROA)
    - Financial health comparison (D/E, current ratio, etc.)
    - Ranking within peer group
    - Strength/weakness identification

    Example:
        comparator = PeerComparator()

        # Compare valuation
        valuation = await comparator.compare_valuation("AAPL", ["MSFT", "GOOGL"])

        # Get complete comparison
        result = await comparator.compare_all("AAPL", ["MSFT", "GOOGL"])
        print(f"Overall score: {result.overall_score}/100")
    """

    # Metric categories configuration
    VALUATION_METRICS = [
        "pe_ratio", "forward_pe", "pb_ratio", "ps_ratio", "ev_ebitda", "peg_ratio"
    ]
    GROWTH_METRICS = [
        "revenue_growth", "earnings_growth", "revenue_growth_yoy", "earnings_growth_yoy"
    ]
    PROFITABILITY_METRICS = [
        "profit_margin", "operating_margin", "gross_margin", "roe", "roa", "roic"
    ]
    FINANCIAL_HEALTH_METRICS = [
        "debt_to_equity", "current_ratio", "quick_ratio", "free_cash_flow"
    ]

    # Metrics where lower is better
    LOWER_IS_BETTER = ["pe_ratio", "forward_pe", "pb_ratio", "ps_ratio", "ev_ebitda", "peg_ratio", "debt_to_equity"]

    def __init__(self, metrics_helper: Optional[PeerMetrics] = None):
        """
        Initialize PeerComparator.

        Args:
            metrics_helper: Optional PeerMetrics instance (creates new if not provided)
        """
        self._metrics_helper = metrics_helper or PeerMetrics()
        logger.info("peer_comparator_initialized")

    async def compare_valuation(
        self, ticker: str, peers: List[str]
    ) -> CategoryComparison:
        """
        Compare valuation metrics across peer group.

        Args:
            ticker: Focus ticker symbol
            peers: List of peer ticker symbols

        Returns:
            CategoryComparison for valuation metrics

        Raises:
            DataFetchError: If metric fetching fails
        """
        logger.info("comparing_valuation", ticker=ticker, peer_count=len(peers))

        return await self._compare_category(
            ticker, peers, MetricCategory.VALUATION, self.VALUATION_METRICS
        )

    async def compare_growth(
        self, ticker: str, peers: List[str]
    ) -> CategoryComparison:
        """
        Compare growth metrics across peer group.

        Args:
            ticker: Focus ticker symbol
            peers: List of peer ticker symbols

        Returns:
            CategoryComparison for growth metrics
        """
        logger.info("comparing_growth", ticker=ticker, peer_count=len(peers))

        return await self._compare_category(
            ticker, peers, MetricCategory.GROWTH, self.GROWTH_METRICS
        )

    async def compare_profitability(
        self, ticker: str, peers: List[str]
    ) -> CategoryComparison:
        """
        Compare profitability metrics across peer group.

        Args:
            ticker: Focus ticker symbol
            peers: List of peer ticker symbols

        Returns:
            CategoryComparison for profitability metrics
        """
        logger.info("comparing_profitability", ticker=ticker, peer_count=len(peers))

        return await self._compare_category(
            ticker, peers, MetricCategory.PROFITABILITY, self.PROFITABILITY_METRICS
        )

    async def compare_financial_health(
        self, ticker: str, peers: List[str]
    ) -> CategoryComparison:
        """
        Compare financial health metrics across peer group.

        Args:
            ticker: Focus ticker symbol
            peers: List of peer ticker symbols

        Returns:
            CategoryComparison for financial health metrics
        """
        logger.info("comparing_financial_health", ticker=ticker, peer_count=len(peers))

        return await self._compare_category(
            ticker, peers, MetricCategory.FINANCIAL_HEALTH, self.FINANCIAL_HEALTH_METRICS
        )

    async def compare_all(
        self, ticker: str, peers: List[str], weights: Optional[Dict[str, float]] = None
    ) -> PeerComparisonResult:
        """
        Perform comprehensive comparison across all categories.

        Args:
            ticker: Focus ticker symbol
            peers: List of peer ticker symbols
            weights: Optional category weights for overall score
                    (default: equal weight)

        Returns:
            Complete PeerComparisonResult

        Raises:
            DataFetchError: If metric fetching fails
        """
        logger.info("comparing_all_categories", ticker=ticker, peer_count=len(peers))

        # Default equal weights
        if weights is None:
            weights = {
                "valuation": 0.25,
                "growth": 0.25,
                "profitability": 0.25,
                "financial_health": 0.25,
            }

        # Fetch all metrics once
        all_tickers = [ticker] + peers
        all_metrics = await self._metrics_helper.get_peer_metrics(all_tickers)

        # Compare each category
        result = PeerComparisonResult(ticker=ticker, peers=peers)

        try:
            result.valuation = await self.compare_valuation(ticker, peers)
        except Exception as e:
            logger.warning("valuation_comparison_failed", error=str(e))

        try:
            result.growth = await self.compare_growth(ticker, peers)
        except Exception as e:
            logger.warning("growth_comparison_failed", error=str(e))

        try:
            result.profitability = await self.compare_profitability(ticker, peers)
        except Exception as e:
            logger.warning("profitability_comparison_failed", error=str(e))

        try:
            result.financial_health = await self.compare_financial_health(ticker, peers)
        except Exception as e:
            logger.warning("financial_health_comparison_failed", error=str(e))

        # Calculate overall score
        category_scores = result.get_category_scores()
        if category_scores:
            weighted_sum = sum(
                score * weights.get(cat, 0.25)
                for cat, score in category_scores.items()
            )
            total_weight = sum(weights.get(cat, 0.25) for cat in category_scores.keys())
            result.overall_score = weighted_sum / total_weight if total_weight > 0 else 0

            # Calculate overall ranking
            all_scores = {}
            for t in all_tickers:
                if t == ticker:
                    all_scores[t] = result.overall_score
                # We'd need to calculate for other tickers too for true ranking
                # For simplicity, we'll estimate based on percentile

            logger.info(
                "comparison_complete",
                ticker=ticker,
                overall_score=result.overall_score,
            )

        return result

    async def rank_in_peer_group(
        self, ticker: str, peers: List[str], metric: str
    ) -> Tuple[int, int, float]:
        """
        Determine where ticker ranks in peer group for a specific metric.

        Args:
            ticker: Focus ticker symbol
            peers: List of peer ticker symbols
            metric: Metric name to rank by

        Returns:
            Tuple of (rank, total_ranked, value)
            rank: 1-based ranking (1 = best)
            total_ranked: Total number of tickers with valid data
            value: Ticker's value for the metric

        Raises:
            DataFetchError: If metric fetching fails
        """
        logger.info("ranking_in_peer_group", ticker=ticker, metric=metric)

        all_tickers = [ticker] + peers
        all_metrics = await self._metrics_helper.get_peer_metrics(all_tickers)

        # Determine ranking order
        higher_is_better = metric not in self.LOWER_IS_BETTER

        # Get ranked list
        ranked = self._metrics_helper.get_metric_ranking(
            all_metrics, metric, ascending=not higher_is_better
        )

        # Find ticker's position
        ticker_rank = None
        ticker_value = None
        for idx, (t, val) in enumerate(ranked, 1):
            if t == ticker:
                ticker_rank = idx
                ticker_value = val
                break

        if ticker_rank is None:
            logger.warning("ticker_not_in_ranking", ticker=ticker, metric=metric)
            return (0, len(ranked), None)

        logger.info(
            "ranking_complete",
            ticker=ticker,
            metric=metric,
            rank=ticker_rank,
            total=len(ranked),
            value=ticker_value,
        )

        return (ticker_rank, len(ranked), ticker_value)

    async def _compare_category(
        self,
        ticker: str,
        peers: List[str],
        category: MetricCategory,
        metric_names: List[str],
    ) -> CategoryComparison:
        """
        Internal method to compare a category of metrics.

        Args:
            ticker: Focus ticker symbol
            peers: List of peer ticker symbols
            category: Metric category
            metric_names: List of metric names in category

        Returns:
            CategoryComparison object
        """
        all_tickers = [ticker] + peers
        all_metrics = await self._metrics_helper.get_peer_metrics(all_tickers)

        if ticker not in all_metrics:
            raise DataFetchError(
                f"Failed to fetch metrics for focus ticker {ticker}",
                ticker=ticker,
            )

        ticker_metrics = all_metrics[ticker]
        comparisons = {}
        percentiles = []
        strengths = []
        weaknesses = []

        for metric_name in metric_names:
            # Calculate stats for this metric
            stats = self._metrics_helper.calculate_metric_stats(all_metrics, metric_name)

            if not stats or stats.count < 2:
                logger.debug("insufficient_data_for_metric", metric=metric_name)
                continue

            ticker_value = ticker_metrics.get_metric(metric_name)

            # Calculate percentile and differences
            percentile = stats.get_percentile(ticker_value) if ticker_value is not None else 0

            vs_median_pct = None
            vs_average_pct = None
            if ticker_value is not None and stats.median != 0:
                vs_median_pct = ((ticker_value - stats.median) / stats.median) * 100
            if ticker_value is not None and stats.mean != 0:
                vs_average_pct = ((ticker_value - stats.mean) / stats.mean) * 100

            # Get ranking
            higher_is_better = metric_name not in self.LOWER_IS_BETTER
            ranked = self._metrics_helper.get_metric_ranking(
                all_metrics, metric_name, ascending=not higher_is_better
            )

            ranking = None
            for idx, (t, _) in enumerate(ranked, 1):
                if t == ticker:
                    ranking = idx
                    break

            # Check if outlier
            is_outlier = stats.is_outlier(ticker_value) if ticker_value is not None else False

            comparison = MetricComparison(
                metric_name=metric_name,
                ticker_value=ticker_value,
                peer_median=stats.median,
                peer_average=stats.mean,
                peer_min=stats.min_value,
                peer_max=stats.max_value,
                percentile_rank=percentile,
                vs_median_pct=vs_median_pct,
                vs_average_pct=vs_average_pct,
                is_outlier=is_outlier,
                ranking=ranking,
                total_ranked=len(ranked),
            )

            comparisons[metric_name] = comparison
            percentiles.append(percentile)

            # Identify strengths and weaknesses
            if comparison.is_better_than_median(higher_is_better):
                if percentile >= 75:
                    strengths.append(metric_name)
            else:
                if percentile <= 25:
                    weaknesses.append(metric_name)

        # Calculate overall category score
        overall_score = sum(percentiles) / len(percentiles) if percentiles else 0

        category_result = CategoryComparison(
            category=category,
            metrics=comparisons,
            overall_score=overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
        )

        logger.info(
            "category_comparison_complete",
            ticker=ticker,
            category=category.value,
            score=overall_score,
            metrics_compared=len(comparisons),
            strengths=len(strengths),
            weaknesses=len(weaknesses),
        )

        return category_result

    def get_metric_interpretation(
        self, metric_name: str, comparison: MetricComparison
    ) -> str:
        """
        Get human-readable interpretation of a metric comparison.

        Args:
            metric_name: Name of the metric
            comparison: MetricComparison object

        Returns:
            Text interpretation
        """
        if comparison.ticker_value is None:
            return f"{metric_name}: No data available"

        higher_is_better = metric_name not in self.LOWER_IS_BETTER
        relative_pos = "above" if comparison.is_better_than_median(higher_is_better) else "below"

        interpretation = (
            f"{metric_name}: {comparison.ticker_value:.2f} "
            f"(Rank {comparison.ranking}/{comparison.total_ranked}, "
            f"{comparison.percentile_rank:.0f}th percentile, "
            f"{abs(comparison.vs_median_pct):.1f}% {relative_pos} peer median)"
        )

        return interpretation
