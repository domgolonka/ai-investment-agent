"""
Peer Comparison Visualizer - Generate tables, charts, and reports for peer analysis.

This module provides utilities for formatting peer comparison data for
display, reporting, and visualization.
"""

import structlog
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from src.peers.comparator import (
    PeerComparisonResult,
    CategoryComparison,
    MetricComparison,
    PeerComparator,
)
from src.peers.metrics import PeerMetrics, TickerMetrics

logger = structlog.get_logger(__name__)


def generate_comparison_table(
    ticker: str,
    peers: List[str],
    metrics_data: Dict[str, TickerMetrics],
    metric_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a tabular comparison of metrics across tickers.

    Args:
        ticker: Focus ticker symbol
        peers: List of peer ticker symbols
        metrics_data: Dict mapping ticker to TickerMetrics
        metric_names: Optional list of specific metrics to include

    Returns:
        Dict containing table structure suitable for display:
        {
            "headers": ["Ticker", "Metric1", "Metric2", ...],
            "rows": [
                ["AAPL", 25.5, 0.35, ...],
                ["MSFT", 28.3, 0.32, ...],
                ...
            ],
            "focus_ticker": "AAPL",
            "timestamp": "2024-01-15 10:30:00"
        }

    Example:
        table = generate_comparison_table("AAPL", ["MSFT", "GOOGL"], metrics)
        # Display with pandas, rich, or custom formatter
        df = pd.DataFrame(table["rows"], columns=table["headers"])
    """
    logger.info(
        "generating_comparison_table",
        ticker=ticker,
        peer_count=len(peers),
    )

    all_tickers = [ticker] + peers

    # Determine which metrics to include
    if metric_names is None:
        # Use all metrics from the first ticker with data
        sample_ticker = next(
            (t for t in all_tickers if t in metrics_data), None
        )
        if sample_ticker:
            sample_metrics = metrics_data[sample_ticker]
            metric_names = [
                k for k in sample_metrics.__dict__.keys()
                if k not in ["ticker", "timestamp", "source"]
                and sample_metrics.get_metric(k) is not None
            ]
        else:
            metric_names = []

    # Build table
    headers = ["Ticker"] + [_format_metric_name(m) for m in metric_names]
    rows = []

    for t in all_tickers:
        if t not in metrics_data:
            continue

        ticker_metrics = metrics_data[t]
        row = [t]

        for metric_name in metric_names:
            value = ticker_metrics.get_metric(metric_name)
            formatted_value = _format_metric_value(metric_name, value)
            row.append(formatted_value)

        rows.append(row)

    table = {
        "headers": headers,
        "rows": rows,
        "focus_ticker": ticker,
        "peer_count": len(peers),
        "metric_count": len(metric_names),
        "timestamp": datetime.utcnow().isoformat(),
    }

    logger.info(
        "comparison_table_generated",
        ticker=ticker,
        rows=len(rows),
        columns=len(headers),
    )

    return table


def generate_ranking_data(
    ticker: str,
    peers: List[str],
    comparison_result: PeerComparisonResult,
) -> Dict[str, Any]:
    """
    Generate ranking data for visualization (charts, graphs).

    Args:
        ticker: Focus ticker symbol
        peers: List of peer ticker symbols
        comparison_result: Complete PeerComparisonResult

    Returns:
        Dict containing ranking data suitable for charting:
        {
            "category_scores": {
                "valuation": 65.5,
                "growth": 78.2,
                "profitability": 82.1,
                "financial_health": 71.3
            },
            "overall_score": 74.3,
            "metric_rankings": {
                "pe_ratio": {"rank": 3, "total": 5, "percentile": 60},
                ...
            },
            "strengths": ["profit_margin", "roe"],
            "weaknesses": ["debt_to_equity"],
            "ticker": "AAPL",
            "timestamp": "2024-01-15 10:30:00"
        }

    Example:
        data = generate_ranking_data("AAPL", peers, comparison)
        # Use with plotting libraries (matplotlib, plotly, etc.)
    """
    logger.info(
        "generating_ranking_data",
        ticker=ticker,
        peer_count=len(peers),
    )

    category_scores = comparison_result.get_category_scores()

    # Collect metric rankings
    metric_rankings = {}
    all_strengths = []
    all_weaknesses = []

    for category_name, category in [
        ("valuation", comparison_result.valuation),
        ("growth", comparison_result.growth),
        ("profitability", comparison_result.profitability),
        ("financial_health", comparison_result.financial_health),
    ]:
        if category is None:
            continue

        all_strengths.extend(category.strengths)
        all_weaknesses.extend(category.weaknesses)

        for metric_name, metric_comp in category.metrics.items():
            metric_rankings[metric_name] = {
                "rank": metric_comp.ranking,
                "total": metric_comp.total_ranked,
                "percentile": metric_comp.percentile_rank,
                "value": metric_comp.ticker_value,
                "peer_median": metric_comp.peer_median,
                "peer_average": metric_comp.peer_average,
                "category": category_name,
            }

    ranking_data = {
        "ticker": ticker,
        "peer_count": len(peers),
        "category_scores": category_scores,
        "overall_score": comparison_result.overall_score,
        "metric_rankings": metric_rankings,
        "strengths": all_strengths,
        "weaknesses": all_weaknesses,
        "timestamp": datetime.utcnow().isoformat(),
    }

    logger.info(
        "ranking_data_generated",
        ticker=ticker,
        overall_score=comparison_result.overall_score,
        strengths=len(all_strengths),
        weaknesses=len(all_weaknesses),
    )

    return ranking_data


def format_comparison_report(
    ticker: str,
    peers: List[str],
    comparison_result: PeerComparisonResult,
    include_details: bool = True,
) -> str:
    """
    Generate a comprehensive markdown-formatted comparison report.

    Args:
        ticker: Focus ticker symbol
        peers: List of peer ticker symbols
        comparison_result: Complete PeerComparisonResult
        include_details: Whether to include detailed metric breakdowns

    Returns:
        Markdown-formatted report string

    Example:
        report = format_comparison_report("AAPL", peers, comparison)
        print(report)
        # Or save to file: Path("report.md").write_text(report)
    """
    logger.info(
        "formatting_comparison_report",
        ticker=ticker,
        peer_count=len(peers),
    )

    lines = []

    # Header
    lines.append(f"# Peer Comparison Report: {ticker}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append(f"**Peer Group:** {', '.join(peers)}")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")

    if comparison_result.overall_score is not None:
        lines.append(f"**Overall Score:** {comparison_result.overall_score:.1f}/100")
        lines.append("")

    category_scores = comparison_result.get_category_scores()
    if category_scores:
        lines.append("**Category Scores:**")
        for category, score in category_scores.items():
            lines.append(f"- {category.replace('_', ' ').title()}: {score:.1f}/100")
        lines.append("")

    # Category Breakdowns
    for category_name, category in [
        ("Valuation", comparison_result.valuation),
        ("Growth", comparison_result.growth),
        ("Profitability", comparison_result.profitability),
        ("Financial Health", comparison_result.financial_health),
    ]:
        if category is None:
            continue

        lines.append(f"## {category_name} Analysis")
        lines.append("")
        lines.append(f"**Score:** {category.overall_score:.1f}/100")
        lines.append("")

        # Strengths and Weaknesses
        if category.strengths:
            lines.append(f"**Strengths ({len(category.strengths)}):**")
            for metric in category.strengths:
                metric_comp = category.metrics.get(metric)
                if metric_comp:
                    lines.append(
                        f"- {_format_metric_name(metric)}: "
                        f"{_format_metric_value(metric, metric_comp.ticker_value)} "
                        f"(Rank {metric_comp.ranking}/{metric_comp.total_ranked}, "
                        f"{metric_comp.percentile_rank:.0f}th percentile)"
                    )
            lines.append("")

        if category.weaknesses:
            lines.append(f"**Weaknesses ({len(category.weaknesses)}):**")
            for metric in category.weaknesses:
                metric_comp = category.metrics.get(metric)
                if metric_comp:
                    lines.append(
                        f"- {_format_metric_name(metric)}: "
                        f"{_format_metric_value(metric, metric_comp.ticker_value)} "
                        f"(Rank {metric_comp.ranking}/{metric_comp.total_ranked}, "
                        f"{metric_comp.percentile_rank:.0f}th percentile)"
                    )
            lines.append("")

        # Detailed metrics table
        if include_details and category.metrics:
            lines.append("### Detailed Metrics")
            lines.append("")
            lines.append("| Metric | Value | Peer Median | Peer Avg | Rank | Percentile |")
            lines.append("|--------|-------|-------------|----------|------|------------|")

            for metric_name, metric_comp in category.metrics.items():
                lines.append(
                    f"| {_format_metric_name(metric_name)} | "
                    f"{_format_metric_value(metric_name, metric_comp.ticker_value)} | "
                    f"{_format_metric_value(metric_name, metric_comp.peer_median)} | "
                    f"{_format_metric_value(metric_name, metric_comp.peer_average)} | "
                    f"{metric_comp.ranking}/{metric_comp.total_ranked} | "
                    f"{metric_comp.percentile_rank:.0f}% |"
                )

            lines.append("")

    # Conclusion
    lines.append("## Key Takeaways")
    lines.append("")

    all_strengths = []
    all_weaknesses = []
    for category in [
        comparison_result.valuation,
        comparison_result.growth,
        comparison_result.profitability,
        comparison_result.financial_health,
    ]:
        if category:
            all_strengths.extend(category.strengths)
            all_weaknesses.extend(category.weaknesses)

    lines.append(
        f"- {ticker} shows strength in {len(all_strengths)} metrics "
        f"across all categories"
    )
    lines.append(
        f"- Areas for improvement: {len(all_weaknesses)} metrics "
        f"below peer median"
    )

    if comparison_result.overall_score:
        if comparison_result.overall_score >= 75:
            position = "strong position"
        elif comparison_result.overall_score >= 50:
            position = "competitive position"
        else:
            position = "below-average position"

        lines.append(
            f"- Overall, {ticker} holds a {position} within its peer group "
            f"({comparison_result.overall_score:.1f}/100)"
        )

    lines.append("")
    lines.append("---")
    lines.append("*This report was generated automatically by the AI Investment Agent.*")

    report = "\n".join(lines)

    logger.info(
        "comparison_report_formatted",
        ticker=ticker,
        lines=len(lines),
    )

    return report


def format_metric_summary(
    metric_name: str, comparison: MetricComparison, include_peers: bool = True
) -> str:
    """
    Format a single metric comparison as a text summary.

    Args:
        metric_name: Name of the metric
        comparison: MetricComparison object
        include_peers: Whether to include peer statistics

    Returns:
        Formatted text summary

    Example:
        summary = format_metric_summary("pe_ratio", comparison)
        # Output: "P/E Ratio: 25.5 (Rank 2/5, 80th percentile, vs median: 23.2)"
    """
    if comparison.ticker_value is None:
        return f"{_format_metric_name(metric_name)}: No data"

    parts = [
        f"{_format_metric_name(metric_name)}: {_format_metric_value(metric_name, comparison.ticker_value)}",
    ]

    if comparison.ranking and comparison.total_ranked:
        parts.append(f"Rank {comparison.ranking}/{comparison.total_ranked}")

    parts.append(f"{comparison.percentile_rank:.0f}th percentile")

    if include_peers and comparison.peer_median is not None:
        parts.append(f"vs median: {_format_metric_value(metric_name, comparison.peer_median)}")

    return " (".join([parts[0], ", ".join(parts[1:])]) + ")"


def generate_category_summary(category: CategoryComparison) -> Dict[str, Any]:
    """
    Generate a summary dictionary for a category comparison.

    Args:
        category: CategoryComparison object

    Returns:
        Summary dict suitable for API responses or JSON export

    Example:
        summary = generate_category_summary(valuation_comparison)
        # Returns: {"category": "valuation", "score": 75.5, ...}
    """
    return {
        "category": category.category.value,
        "overall_score": category.overall_score,
        "metrics_analyzed": len(category.metrics),
        "strengths": [
            {
                "metric": metric,
                "percentile": category.metrics[metric].percentile_rank,
                "ranking": f"{category.metrics[metric].ranking}/{category.metrics[metric].total_ranked}",
            }
            for metric in category.strengths
        ],
        "weaknesses": [
            {
                "metric": metric,
                "percentile": category.metrics[metric].percentile_rank,
                "ranking": f"{category.metrics[metric].ranking}/{category.metrics[metric].total_ranked}",
            }
            for metric in category.weaknesses
        ],
        "summary": category.get_summary(),
    }


def _format_metric_name(metric_name: str) -> str:
    """Format metric name for display."""
    # Map internal names to display names
    display_names = {
        "pe_ratio": "P/E Ratio",
        "forward_pe": "Forward P/E",
        "pb_ratio": "P/B Ratio",
        "ps_ratio": "P/S Ratio",
        "ev_ebitda": "EV/EBITDA",
        "peg_ratio": "PEG Ratio",
        "revenue_growth": "Revenue Growth",
        "earnings_growth": "Earnings Growth",
        "revenue_growth_yoy": "Revenue Growth YoY",
        "earnings_growth_yoy": "Earnings Growth YoY",
        "profit_margin": "Profit Margin",
        "operating_margin": "Operating Margin",
        "gross_margin": "Gross Margin",
        "roe": "ROE",
        "roa": "ROA",
        "roic": "ROIC",
        "debt_to_equity": "Debt/Equity",
        "current_ratio": "Current Ratio",
        "quick_ratio": "Quick Ratio",
        "free_cash_flow": "Free Cash Flow",
        "market_cap": "Market Cap",
        "enterprise_value": "Enterprise Value",
        "beta": "Beta",
        "dividend_yield": "Dividend Yield",
        "total_cash": "Total Cash",
        "total_debt": "Total Debt",
    }

    return display_names.get(metric_name, metric_name.replace("_", " ").title())


def _format_metric_value(metric_name: str, value: Optional[float]) -> str:
    """Format metric value for display."""
    if value is None:
        return "N/A"

    # Determine formatting based on metric type
    if metric_name in ["market_cap", "enterprise_value", "total_cash", "total_debt", "free_cash_flow"]:
        # Large dollar amounts - use billions/millions
        if abs(value) >= 1e9:
            return f"${value / 1e9:.2f}B"
        elif abs(value) >= 1e6:
            return f"${value / 1e6:.2f}M"
        else:
            return f"${value:,.0f}"

    elif metric_name in [
        "profit_margin", "operating_margin", "gross_margin",
        "roe", "roa", "roic",
        "revenue_growth", "earnings_growth", "revenue_growth_yoy", "earnings_growth_yoy",
        "dividend_yield"
    ]:
        # Percentages
        return f"{value * 100:.2f}%" if abs(value) < 1 else f"{value:.2f}%"

    elif metric_name in ["pe_ratio", "forward_pe", "pb_ratio", "ps_ratio", "ev_ebitda", "peg_ratio"]:
        # Ratios
        return f"{value:.2f}x"

    elif metric_name in ["current_ratio", "quick_ratio", "debt_to_equity"]:
        # Ratios (no 'x' suffix)
        return f"{value:.2f}"

    elif metric_name == "beta":
        # Beta (3 decimal places)
        return f"{value:.3f}"

    else:
        # Default formatting
        return f"{value:,.2f}"


# Convenience functions for common use cases

def create_quick_comparison_table(
    ticker: str,
    peers: List[str],
    metrics_data: Dict[str, TickerMetrics],
    key_metrics: Optional[List[str]] = None,
) -> str:
    """
    Create a simple text-based comparison table for quick viewing.

    Args:
        ticker: Focus ticker
        peers: Peer tickers
        metrics_data: Metrics data
        key_metrics: Optional list of specific metrics to show

    Returns:
        Text table string
    """
    if key_metrics is None:
        key_metrics = ["pe_ratio", "revenue_growth", "profit_margin", "roe", "debt_to_equity"]

    table_data = generate_comparison_table(ticker, peers, metrics_data, key_metrics)

    # Build text table
    lines = []
    headers = table_data["headers"]
    rows = table_data["rows"]

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Create separator
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    # Header
    lines.append(separator)
    header_row = "|" + "|".join(
        f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)
    ) + "|"
    lines.append(header_row)
    lines.append(separator)

    # Data rows
    for row in rows:
        data_row = "|" + "|".join(
            f" {str(cell):<{col_widths[i]}} " for i, cell in enumerate(row)
        ) + "|"
        lines.append(data_row)

    lines.append(separator)

    return "\n".join(lines)
