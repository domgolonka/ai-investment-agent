"""
UI Components Package
Reusable Streamlit components for the AI Investment Agent.
"""

from .ticker_input import render_ticker_input
from .decision_card import render_decision_card
from .analysis_view import render_analysis_sections
from .chart_view import render_price_chart, render_equity_curve
from .analysis_history_card import (
    render_analysis_history_card,
    render_analysis_history_list,
    render_signal_filter,
    render_analysis_stats
)
from .watchlist_view import (
    render_watchlist,
    render_watchlist_item,
    render_convert_modal
)

__all__ = [
    "render_ticker_input",
    "render_decision_card",
    "render_analysis_sections",
    "render_price_chart",
    "render_equity_curve",
    # Analysis history components
    "render_analysis_history_card",
    "render_analysis_history_list",
    "render_signal_filter",
    "render_analysis_stats",
    # Watchlist components
    "render_watchlist",
    "render_watchlist_item",
    "render_convert_modal",
]
