"""
Analysis History Card Component
Displays a compact card showing analysis summary with signal and actions.
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Callable


def get_signal_color(signal: str) -> tuple:
    """
    Get colors for a trading signal.

    Args:
        signal: Signal type ('BUY', 'SELL', 'HOLD', 'UNKNOWN')

    Returns:
        Tuple of (background_color, text_color, border_color)
    """
    colors = {
        "BUY": ("#d4edda", "#155724", "#28a745"),
        "SELL": ("#f8d7da", "#721c24", "#dc3545"),
        "HOLD": ("#fff3cd", "#856404", "#ffc107"),
        "UNKNOWN": ("#e2e3e5", "#383d41", "#6c757d"),
    }
    return colors.get(signal.upper(), colors["UNKNOWN"])


def get_signal_emoji(signal: str) -> str:
    """Get emoji for a signal type."""
    emojis = {
        "BUY": "🟢",
        "SELL": "🔴",
        "HOLD": "🟡",
        "UNKNOWN": "⚪",
    }
    return emojis.get(signal.upper(), "⚪")


def render_analysis_history_card(
    analysis_id: int,
    ticker: str,
    company_name: str,
    signal: str,
    analysis_date: datetime,
    analysis_mode: str,
    show_actions: bool = True,
    on_add_to_watchlist: Optional[Callable] = None,
    key_prefix: str = ""
) -> None:
    """
    Render a compact card showing analysis summary.

    Args:
        analysis_id: Database ID of the analysis
        ticker: Stock ticker symbol
        company_name: Full company name
        signal: Trading signal (BUY/SELL/HOLD/UNKNOWN)
        analysis_date: When the analysis was performed
        analysis_mode: 'quick' or 'deep'
        show_actions: Whether to show action buttons
        on_add_to_watchlist: Callback when add to watchlist is clicked
        key_prefix: Prefix for Streamlit widget keys
    """
    bg_color, text_color, border_color = get_signal_color(signal)
    signal_emoji = get_signal_emoji(signal)

    # Card container
    st.markdown(f"""
        <div style="
            background: white;
            border: 2px solid {border_color};
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h4 style="margin: 0; color: #333;">{signal_emoji} {ticker}</h4>
                    <p style="margin: 0.25rem 0; color: #666; font-size: 0.9em;">{company_name}</p>
                </div>
                <div style="
                    background: {bg_color};
                    color: {text_color};
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 0.85em;
                ">{signal}</div>
            </div>
            <div style="margin-top: 0.5rem; display: flex; gap: 1rem; color: #888; font-size: 0.85em;">
                <span>📅 {analysis_date.strftime('%Y-%m-%d %H:%M')}</span>
                <span>📊 {analysis_mode.capitalize()} Mode</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if show_actions:
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("📄 View Details", key=f"{key_prefix}view_{analysis_id}", use_container_width=True):
                st.session_state[f"view_analysis_{analysis_id}"] = True
                st.rerun()

        with col2:
            if st.button("➕ Add to Watchlist", key=f"{key_prefix}watchlist_{analysis_id}", use_container_width=True):
                if on_add_to_watchlist:
                    on_add_to_watchlist(analysis_id, ticker, company_name)
                else:
                    st.session_state[f"add_to_watchlist_{analysis_id}"] = True
                    st.rerun()

        with col3:
            if st.button("🔄 Re-analyze", key=f"{key_prefix}reanalyze_{analysis_id}", use_container_width=True):
                st.session_state.ticker = ticker
                st.switch_page("pages/1_Single_Analysis.py")


def render_analysis_history_list(
    analyses: list,
    show_actions: bool = True,
    on_add_to_watchlist: Optional[Callable] = None,
    key_prefix: str = ""
) -> None:
    """
    Render a list of analysis history cards.

    Args:
        analyses: List of AnalysisRecord objects
        show_actions: Whether to show action buttons
        on_add_to_watchlist: Callback when add to watchlist is clicked
        key_prefix: Prefix for Streamlit widget keys
    """
    if not analyses:
        st.info("No analyses found. Run an analysis from the Single Analysis page to get started.")
        return

    for i, analysis in enumerate(analyses):
        render_analysis_history_card(
            analysis_id=analysis.id,
            ticker=analysis.ticker,
            company_name=analysis.company_name,
            signal=analysis.signal,
            analysis_date=analysis.analysis_date,
            analysis_mode=analysis.analysis_mode,
            show_actions=show_actions,
            on_add_to_watchlist=on_add_to_watchlist,
            key_prefix=f"{key_prefix}{i}_"
        )


def render_signal_filter(key: str = "signal_filter") -> Optional[str]:
    """
    Render a signal filter dropdown.

    Args:
        key: Streamlit widget key

    Returns:
        Selected signal or None for all
    """
    options = ["All", "BUY", "SELL", "HOLD", "UNKNOWN"]
    selected = st.selectbox("Filter by Signal", options, key=key)
    return None if selected == "All" else selected


def render_analysis_stats(analyses: list) -> None:
    """
    Render summary statistics for a list of analyses.

    Args:
        analyses: List of AnalysisRecord objects
    """
    if not analyses:
        return

    total = len(analyses)
    buy_count = sum(1 for a in analyses if a.signal == "BUY")
    sell_count = sum(1 for a in analyses if a.signal == "SELL")
    hold_count = sum(1 for a in analyses if a.signal == "HOLD")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Analyses", total)

    with col2:
        st.metric("🟢 BUY", buy_count)

    with col3:
        st.metric("🔴 SELL", sell_count)

    with col4:
        st.metric("🟡 HOLD", hold_count)
