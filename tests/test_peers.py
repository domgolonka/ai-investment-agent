"""
Unit tests for the Peer Comparison module.

Tests cover:
- PeerFinder: Peer detection and caching
- PeerMetrics: Metric fetching and aggregation
- PeerComparator: Comparison and ranking
- Visualizer: Report and table generation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.peers.finder import PeerFinder, SectorInfo, PeerGroup
from src.peers.metrics import PeerMetrics, TickerMetrics, PeerGroupStats
from src.peers.comparator import (
    PeerComparator,
    MetricCategory,
    MetricComparison,
    CategoryComparison,
    PeerComparisonResult,
)
from src.peers.visualizer import (
    generate_comparison_table,
    generate_ranking_data,
    format_comparison_report,
    _format_metric_name,
    _format_metric_value,
)
from src.exceptions import DataFetchError, TickerNotFoundError


# ============================================================================
# PeerFinder Tests
# ============================================================================


class TestPeerFinder:
    """Tests for PeerFinder class."""

    @pytest.fixture
    def finder(self):
        """Create PeerFinder instance."""
        return PeerFinder(cache_ttl_hours=1, max_peers=5)

    @pytest.fixture
    def sample_sector_info(self):
        """Sample sector info for testing."""
        return SectorInfo(
            ticker="AAPL",
            sector="Technology",
            industry="Consumer Electronics",
            country="United States",
            market_cap=3000e9,
        )

    def test_sector_info_is_valid(self, sample_sector_info):
        """Test SectorInfo validation."""
        assert sample_sector_info.is_valid() is True

        # Test invalid
        invalid_info = SectorInfo(ticker="TEST", sector=None, industry=None)
        assert invalid_info.is_valid() is False

    def test_sector_info_is_stale(self):
        """Test SectorInfo staleness check."""
        # Fresh data
        fresh = SectorInfo(
            ticker="TEST",
            sector="Tech",
            industry="Software",
            last_updated=datetime.utcnow(),
        )
        assert fresh.is_stale(ttl_hours=24) is False

        # Stale data
        stale = SectorInfo(
            ticker="TEST",
            sector="Tech",
            industry="Software",
            last_updated=datetime.utcnow() - timedelta(hours=48),
        )
        assert stale.is_stale(ttl_hours=24) is True

    def test_peer_group_get_all_tickers(self):
        """Test PeerGroup ticker list."""
        group = PeerGroup(
            focus_ticker="AAPL",
            peers=["MSFT", "GOOGL"],
            sector="Technology",
            industry="Software",
            total_candidates=10,
        )
        assert group.get_all_tickers() == ["AAPL", "MSFT", "GOOGL"]

    def test_cache_stats(self, finder):
        """Test cache statistics."""
        stats = finder.get_cache_stats()
        assert "sector_info_cached" in stats
        assert "industry_groups_cached" in stats
        assert stats["sector_info_cached"] == 0

    def test_clear_cache(self, finder):
        """Test cache clearing."""
        # Add some data to cache
        finder._sector_cache["TEST"] = SectorInfo(
            ticker="TEST", sector="Tech", industry="Software"
        )
        assert len(finder._sector_cache) == 1

        finder.clear_cache()
        assert len(finder._sector_cache) == 0


# ============================================================================
# PeerMetrics Tests
# ============================================================================


class TestPeerMetrics:
    """Tests for PeerMetrics class."""

    @pytest.fixture
    def metrics_helper(self):
        """Create PeerMetrics instance."""
        return PeerMetrics(fetch_timeout=10, max_concurrent=5)

    @pytest.fixture
    def sample_ticker_metrics(self):
        """Sample TickerMetrics for testing."""
        return {
            "AAPL": TickerMetrics(
                ticker="AAPL",
                pe_ratio=28.5,
                revenue_growth=0.08,
                profit_margin=0.25,
                roe=0.45,
                debt_to_equity=1.2,
                market_cap=3000e9,
            ),
            "MSFT": TickerMetrics(
                ticker="MSFT",
                pe_ratio=32.1,
                revenue_growth=0.12,
                profit_margin=0.30,
                roe=0.42,
                debt_to_equity=0.8,
                market_cap=2800e9,
            ),
            "GOOGL": TickerMetrics(
                ticker="GOOGL",
                pe_ratio=25.3,
                revenue_growth=0.15,
                profit_margin=0.28,
                roe=0.38,
                debt_to_equity=0.5,
                market_cap=1800e9,
            ),
        }

    def test_ticker_metrics_to_dict(self):
        """Test TickerMetrics to_dict conversion."""
        metrics = TickerMetrics(
            ticker="TEST",
            pe_ratio=25.0,
            revenue_growth=0.1,
        )
        data = metrics.to_dict()

        assert data["ticker"] == "TEST"
        assert data["pe_ratio"] == 25.0
        assert data["revenue_growth"] == 0.1
        assert "timestamp" not in data
        assert "source" not in data

    def test_ticker_metrics_get_metric(self):
        """Test TickerMetrics get_metric method."""
        metrics = TickerMetrics(ticker="TEST", pe_ratio=25.0)

        assert metrics.get_metric("pe_ratio") == 25.0
        assert metrics.get_metric("revenue_growth") is None
        assert metrics.get_metric("invalid_metric") is None

    def test_calculate_metric_stats(self, metrics_helper, sample_ticker_metrics):
        """Test metric statistics calculation."""
        stats = metrics_helper.calculate_metric_stats(
            sample_ticker_metrics, "pe_ratio"
        )

        assert stats is not None
        assert stats.metric_name == "pe_ratio"
        assert stats.count == 3
        assert stats.median == 28.5
        assert stats.min_value == 25.3
        assert stats.max_value == 32.1

    def test_calculate_metric_stats_insufficient_data(self, metrics_helper):
        """Test metric stats with insufficient data."""
        metrics = {
            "TEST": TickerMetrics(ticker="TEST", pe_ratio=25.0)
        }

        stats = metrics_helper.calculate_metric_stats(metrics, "pe_ratio")
        assert stats is None  # Need at least 2 data points

    def test_peer_group_stats_get_percentile(self):
        """Test percentile calculation."""
        stats = PeerGroupStats(
            metric_name="pe_ratio",
            values=[20.0, 25.0, 30.0, 35.0, 40.0],
            median=30.0,
            mean=30.0,
            std_dev=7.07,
            min_value=20.0,
            max_value=40.0,
            percentile_25=25.0,
            percentile_75=35.0,
            count=5,
        )

        # Test percentile calculation
        assert stats.get_percentile(25.0) == 25.0  # 25th percentile
        assert stats.get_percentile(40.0) == 100.0  # Max value

    def test_peer_group_stats_is_outlier(self):
        """Test outlier detection."""
        stats = PeerGroupStats(
            metric_name="pe_ratio",
            values=[20.0, 22.0, 23.0, 24.0, 25.0],
            median=23.0,
            mean=22.8,
            std_dev=2.0,
            min_value=20.0,
            max_value=25.0,
            percentile_25=22.0,
            percentile_75=24.0,
            count=5,
        )

        # Normal values
        assert stats.is_outlier(23.0) is False
        assert stats.is_outlier(24.0) is False

        # Outlier (beyond 2 std dev)
        assert stats.is_outlier(30.0) is True

    def test_calculate_peer_median(self, metrics_helper, sample_ticker_metrics):
        """Test peer median calculation."""
        medians = metrics_helper.calculate_peer_median(sample_ticker_metrics)

        assert "pe_ratio" in medians
        assert medians["pe_ratio"] == 28.5

    def test_calculate_peer_average(self, metrics_helper, sample_ticker_metrics):
        """Test peer average calculation."""
        averages = metrics_helper.calculate_peer_average(sample_ticker_metrics)

        assert "pe_ratio" in averages
        assert abs(averages["pe_ratio"] - 28.63) < 0.01

    def test_calculate_percentile(self, metrics_helper):
        """Test percentile rank calculation."""
        peer_values = [20.0, 25.0, 30.0, 35.0, 40.0]

        # Test various percentiles
        assert metrics_helper.calculate_percentile(30.0, peer_values) == 50.0
        assert metrics_helper.calculate_percentile(40.0, peer_values) == 80.0
        assert metrics_helper.calculate_percentile(20.0, peer_values) == 0.0

    def test_calculate_percentile_with_none(self, metrics_helper):
        """Test percentile calculation with None values."""
        peer_values = [20.0, None, 30.0, None, 40.0]

        percentile = metrics_helper.calculate_percentile(30.0, peer_values)
        assert percentile == 50.0

    def test_get_metric_ranking(self, metrics_helper, sample_ticker_metrics):
        """Test metric ranking."""
        ranking = metrics_helper.get_metric_ranking(
            sample_ticker_metrics, "pe_ratio", ascending=True
        )

        assert len(ranking) == 3
        assert ranking[0][0] == "GOOGL"  # Lowest P/E
        assert ranking[-1][0] == "MSFT"  # Highest P/E

    def test_safe_float(self):
        """Test safe float conversion."""
        assert PeerMetrics._safe_float(25.5) == 25.5
        assert PeerMetrics._safe_float("25.5") == 25.5
        assert PeerMetrics._safe_float(None) is None
        assert PeerMetrics._safe_float("invalid") is None
        assert PeerMetrics._safe_float(float('nan')) is None
        assert PeerMetrics._safe_float(float('inf')) is None

    def test_get_coverage_report(self, metrics_helper, sample_ticker_metrics):
        """Test coverage report generation."""
        report = metrics_helper.get_coverage_report(sample_ticker_metrics)

        assert report["total_tickers"] == 3
        assert "pe_ratio" in report["metrics"]
        assert report["metrics"]["pe_ratio"]["available"] == 3
        assert report["metrics"]["pe_ratio"]["coverage_pct"] == 100.0


# ============================================================================
# PeerComparator Tests
# ============================================================================


class TestPeerComparator:
    """Tests for PeerComparator class."""

    @pytest.fixture
    def comparator(self):
        """Create PeerComparator instance."""
        return PeerComparator()

    @pytest.fixture
    def sample_metrics(self):
        """Sample metrics for comparison."""
        return {
            "AAPL": TickerMetrics(
                ticker="AAPL",
                pe_ratio=28.5,
                revenue_growth=0.08,
                profit_margin=0.25,
                debt_to_equity=1.2,
            ),
            "MSFT": TickerMetrics(
                ticker="MSFT",
                pe_ratio=32.1,
                revenue_growth=0.12,
                profit_margin=0.30,
                debt_to_equity=0.8,
            ),
        }

    def test_metric_comparison_is_better_than_median(self):
        """Test metric comparison evaluation."""
        comparison = MetricComparison(
            metric_name="pe_ratio",
            ticker_value=25.0,
            peer_median=30.0,
            peer_average=28.0,
            peer_min=20.0,
            peer_max=35.0,
            percentile_rank=40.0,
            vs_median_pct=-16.67,
            vs_average_pct=-10.71,
        )

        # For P/E, lower is better
        assert comparison.is_better_than_median(higher_is_better=False) is True
        assert comparison.is_better_than_median(higher_is_better=True) is False

    def test_metric_comparison_get_relative_strength(self):
        """Test relative strength categorization."""
        # Strong
        strong = MetricComparison(
            metric_name="test",
            ticker_value=100,
            peer_median=50,
            peer_average=50,
            peer_min=0,
            peer_max=100,
            percentile_rank=85.0,
        )
        assert strong.get_relative_strength() == "Strong"

        # Above Average
        above_avg = MetricComparison(
            metric_name="test",
            ticker_value=60,
            peer_median=50,
            peer_average=50,
            peer_min=0,
            peer_max=100,
            percentile_rank=60.0,
        )
        assert above_avg.get_relative_strength() == "Above Average"

        # Below Average
        below_avg = MetricComparison(
            metric_name="test",
            ticker_value=40,
            peer_median=50,
            peer_average=50,
            peer_min=0,
            peer_max=100,
            percentile_rank=40.0,
        )
        assert below_avg.get_relative_strength() == "Below Average"

        # Weak
        weak = MetricComparison(
            metric_name="test",
            ticker_value=10,
            peer_median=50,
            peer_average=50,
            peer_min=0,
            peer_max=100,
            percentile_rank=20.0,
        )
        assert weak.get_relative_strength() == "Weak"

    def test_category_comparison_get_summary(self):
        """Test category comparison summary."""
        category = CategoryComparison(
            category=MetricCategory.VALUATION,
            metrics={},
            overall_score=75.5,
            strengths=["pe_ratio", "pb_ratio"],
            weaknesses=["ev_ebitda"],
        )

        summary = category.get_summary()
        assert "Valuation" in summary
        assert "75.5" in summary
        assert "2 strengths" in summary
        assert "1 weakness" in summary

    def test_peer_comparison_result_get_category_scores(self):
        """Test category score extraction."""
        valuation = CategoryComparison(
            category=MetricCategory.VALUATION,
            metrics={},
            overall_score=75.0,
        )
        growth = CategoryComparison(
            category=MetricCategory.GROWTH,
            metrics={},
            overall_score=80.0,
        )

        result = PeerComparisonResult(
            ticker="AAPL",
            peers=["MSFT", "GOOGL"],
            valuation=valuation,
            growth=growth,
        )

        scores = result.get_category_scores()
        assert scores["valuation"] == 75.0
        assert scores["growth"] == 80.0

    def test_get_metric_interpretation(self, comparator):
        """Test metric interpretation generation."""
        comparison = MetricComparison(
            metric_name="pe_ratio",
            ticker_value=28.5,
            peer_median=30.0,
            peer_average=29.0,
            peer_min=25.0,
            peer_max=35.0,
            percentile_rank=45.0,
            vs_median_pct=-5.0,
            vs_average_pct=-1.7,
            ranking=2,
            total_ranked=5,
        )

        interpretation = comparator.get_metric_interpretation("pe_ratio", comparison)

        assert "pe_ratio" in interpretation
        assert "28.5" in interpretation
        assert "2/5" in interpretation
        assert "45" in interpretation


# ============================================================================
# Visualizer Tests
# ============================================================================


class TestVisualizer:
    """Tests for visualizer functions."""

    @pytest.fixture
    def sample_metrics(self):
        """Sample metrics for visualization."""
        return {
            "AAPL": TickerMetrics(
                ticker="AAPL",
                pe_ratio=28.5,
                revenue_growth=0.08,
            ),
            "MSFT": TickerMetrics(
                ticker="MSFT",
                pe_ratio=32.1,
                revenue_growth=0.12,
            ),
        }

    @pytest.fixture
    def sample_comparison_result(self):
        """Sample comparison result."""
        valuation = CategoryComparison(
            category=MetricCategory.VALUATION,
            metrics={
                "pe_ratio": MetricComparison(
                    metric_name="pe_ratio",
                    ticker_value=28.5,
                    peer_median=30.0,
                    peer_average=29.0,
                    peer_min=25.0,
                    peer_max=35.0,
                    percentile_rank=45.0,
                    vs_median_pct=-5.0,
                    ranking=2,
                    total_ranked=3,
                )
            },
            overall_score=75.0,
            strengths=["pe_ratio"],
            weaknesses=[],
        )

        return PeerComparisonResult(
            ticker="AAPL",
            peers=["MSFT", "GOOGL"],
            valuation=valuation,
            overall_score=75.0,
        )

    def test_format_metric_name(self):
        """Test metric name formatting."""
        assert _format_metric_name("pe_ratio") == "P/E Ratio"
        assert _format_metric_name("revenue_growth") == "Revenue Growth"
        assert _format_metric_name("roe") == "ROE"
        assert _format_metric_name("debt_to_equity") == "Debt/Equity"

    def test_format_metric_value(self):
        """Test metric value formatting."""
        # Large amounts
        assert _format_metric_value("market_cap", 3000e9) == "$3000.00B"
        assert _format_metric_value("market_cap", 500e6) == "$500.00M"

        # Percentages
        assert _format_metric_value("profit_margin", 0.25) == "25.00%"
        assert _format_metric_value("revenue_growth", 0.15) == "15.00%"

        # Ratios
        assert _format_metric_value("pe_ratio", 28.5) == "28.50x"
        assert _format_metric_value("current_ratio", 1.5) == "1.50"

        # Beta
        assert _format_metric_value("beta", 1.234) == "1.234"

        # None
        assert _format_metric_value("pe_ratio", None) == "N/A"

    def test_generate_comparison_table(self, sample_metrics):
        """Test comparison table generation."""
        table = generate_comparison_table(
            ticker="AAPL",
            peers=["MSFT"],
            metrics_data=sample_metrics,
            metric_names=["pe_ratio", "revenue_growth"],
        )

        assert table["focus_ticker"] == "AAPL"
        assert table["peer_count"] == 1
        assert "headers" in table
        assert "rows" in table
        assert len(table["rows"]) == 2  # AAPL + MSFT

    def test_generate_ranking_data(self, sample_comparison_result):
        """Test ranking data generation."""
        data = generate_ranking_data(
            ticker="AAPL",
            peers=["MSFT", "GOOGL"],
            comparison_result=sample_comparison_result,
        )

        assert data["ticker"] == "AAPL"
        assert data["peer_count"] == 2
        assert data["overall_score"] == 75.0
        assert "category_scores" in data
        assert "metric_rankings" in data

    def test_format_comparison_report(self, sample_comparison_result):
        """Test comparison report formatting."""
        report = format_comparison_report(
            ticker="AAPL",
            peers=["MSFT", "GOOGL"],
            comparison_result=sample_comparison_result,
            include_details=True,
        )

        assert "# Peer Comparison Report: AAPL" in report
        assert "MSFT, GOOGL" in report
        assert "Overall Score" in report
        assert "Valuation Analysis" in report


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestPeerModuleIntegration:
    """Integration tests requiring actual API calls."""

    @pytest.mark.asyncio
    async def test_end_to_end_comparison(self):
        """Test complete peer comparison workflow."""
        # This test would require actual API access
        # Skipped in unit tests, run separately with --integration flag
        pytest.skip("Requires live API access")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
