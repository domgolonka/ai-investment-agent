"""
Analysis History Page
Browse and manage past stock analyses with filtering and watchlist integration.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis import AnalysisHistoryStorage, AnalysisRecord
from src.portfolio import PortfolioStorage, WatchlistItem
from ui.components.analysis_history_card import (
    render_analysis_history_card,
    render_signal_filter,
    render_analysis_stats,
    get_signal_color,
    get_signal_emoji
)
from ui.components.analysis_view import render_analysis_sections

st.set_page_config(
    page_title="Analysis History - AI Investment Agent",
    page_icon="📜",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .history-header {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .filter-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)


def render_analysis_detail(analysis: AnalysisRecord) -> None:
    """Render full details for a single analysis."""
    bg_color, text_color, border_color = get_signal_color(analysis.signal)
    signal_emoji = get_signal_emoji(analysis.signal)

    # Header
    st.markdown(f"""
        <div style="
            background: white;
            border: 2px solid {border_color};
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin: 0;">{signal_emoji} {analysis.ticker}</h2>
                    <p style="margin: 0.5rem 0; color: #666;">{analysis.company_name}</p>
                </div>
                <div style="
                    background: {bg_color};
                    color: {text_color};
                    padding: 0.5rem 1.5rem;
                    border-radius: 25px;
                    font-weight: bold;
                    font-size: 1.2em;
                ">{analysis.signal}</div>
            </div>
            <div style="margin-top: 1rem; color: #888;">
                <span>📅 {analysis.analysis_date.strftime('%Y-%m-%d %H:%M:%S')}</span>
                <span style="margin-left: 2rem;">📊 {analysis.analysis_mode.capitalize()} Mode</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Convert analysis to result dict for render_analysis_sections
    result = {
        "final_trade_decision": analysis.final_trade_decision,
        "market_report": analysis.market_report,
        "sentiment_report": analysis.sentiment_report,
        "news_report": analysis.news_report,
        "fundamentals_report": analysis.fundamentals_report,
        "investment_plan": analysis.investment_plan,
        "trader_investment_plan": analysis.trader_investment_plan,
        "consultant_review": analysis.consultant_review,
        "investment_debate_state": analysis.investment_debate_state,
        "risk_debate_state": analysis.risk_debate_state,
        "red_flags": analysis.red_flags,
        "pre_screening_result": analysis.pre_screening_result,
    }

    render_analysis_sections(result)


def main():
    """Main analysis history page."""

    st.markdown('<div class="history-header">', unsafe_allow_html=True)
    st.markdown("# 📜 Analysis History")
    st.markdown("Browse and manage your past stock analyses")
    st.markdown('</div>', unsafe_allow_html=True)

    # Initialize storage
    history_storage = AnalysisHistoryStorage()
    portfolio_storage = PortfolioStorage()

    # Check if we're viewing a specific analysis
    viewing_analysis_id = None
    for key in st.session_state:
        if key.startswith("view_analysis_") and st.session_state[key]:
            viewing_analysis_id = int(key.replace("view_analysis_", ""))
            break

    # Check if we're adding to watchlist
    adding_to_watchlist_id = None
    for key in st.session_state:
        if key.startswith("add_to_watchlist_") and st.session_state[key]:
            adding_to_watchlist_id = int(key.replace("add_to_watchlist_", ""))
            break

    # Handle adding to watchlist modal
    if adding_to_watchlist_id:
        analysis = history_storage.get_analysis_by_id(adding_to_watchlist_id)
        if analysis:
            st.markdown("### Add to Watchlist")

            portfolios = portfolio_storage.list_portfolios()
            if not portfolios:
                st.warning("No portfolios found. Create a portfolio first on the Portfolio page.")
                if st.button("Cancel"):
                    st.session_state[f"add_to_watchlist_{adding_to_watchlist_id}"] = False
                    st.rerun()
            else:
                col1, col2 = st.columns(2)

                with col1:
                    selected_portfolio = st.selectbox(
                        "Select Portfolio",
                        portfolios,
                        key="watchlist_modal_portfolio"
                    )

                with col2:
                    target_price = st.number_input(
                        "Target Price ($)",
                        min_value=0.0,
                        value=0.0,
                        step=0.01,
                        key="watchlist_modal_price"
                    )

                col_add, col_cancel = st.columns(2)

                with col_add:
                    if st.button("Add to Watchlist", type="primary", use_container_width=True):
                        if portfolio_storage.is_in_watchlist(selected_portfolio, analysis.ticker):
                            st.warning(f"{analysis.ticker} is already in the watchlist")
                        else:
                            try:
                                item = WatchlistItem(
                                    ticker=analysis.ticker,
                                    company_name=analysis.company_name,
                                    portfolio_name=selected_portfolio,
                                    analysis_id=analysis.id,
                                    target_price=target_price if target_price > 0 else None
                                )
                                portfolio_storage.add_to_watchlist(item)
                                st.success(f"Added {analysis.ticker} to watchlist!")
                                st.session_state[f"add_to_watchlist_{adding_to_watchlist_id}"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to add: {str(e)}")

                with col_cancel:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state[f"add_to_watchlist_{adding_to_watchlist_id}"] = False
                        st.rerun()

            st.markdown("---")

    # Handle viewing analysis detail
    if viewing_analysis_id:
        analysis = history_storage.get_analysis_by_id(viewing_analysis_id)

        if analysis:
            if st.button("← Back to History"):
                st.session_state[f"view_analysis_{viewing_analysis_id}"] = False
                st.rerun()

            st.markdown("---")
            render_analysis_detail(analysis)
        else:
            st.error("Analysis not found")
            if st.button("← Back to History"):
                st.session_state[f"view_analysis_{viewing_analysis_id}"] = False
                st.rerun()

        return

    # Sidebar filters
    with st.sidebar:
        st.markdown("## Filters")

        # Ticker search
        ticker_search = st.text_input(
            "Search Ticker",
            placeholder="e.g., AAPL",
            key="ticker_search"
        ).strip().upper()

        # Signal filter
        signal_filter = render_signal_filter(key="history_signal_filter")

        # Date range
        st.markdown("### Date Range")
        date_options = ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Custom"]
        date_range = st.selectbox("Period", date_options, key="date_range")

        start_date = None
        end_date = None

        if date_range == "Last 7 Days":
            start_date = datetime.now() - timedelta(days=7)
        elif date_range == "Last 30 Days":
            start_date = datetime.now() - timedelta(days=30)
        elif date_range == "Last 90 Days":
            start_date = datetime.now() - timedelta(days=90)
        elif date_range == "Custom":
            start_date = st.date_input("Start Date", key="custom_start")
            end_date = st.date_input("End Date", key="custom_end")
            if start_date:
                start_date = datetime.combine(start_date, datetime.min.time())
            if end_date:
                end_date = datetime.combine(end_date, datetime.max.time())

        # Results limit
        limit = st.slider("Results Limit", 10, 100, 50, key="results_limit")

        # Search button
        search_btn = st.button("🔍 Search", type="primary", use_container_width=True)

    # Main content
    # Get analyses based on filters
    analyses = history_storage.search_analyses(
        ticker=ticker_search if ticker_search else None,
        signal=signal_filter,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    # Stats
    render_analysis_stats(analyses)
    st.markdown("---")

    # Results
    if not analyses:
        st.info("No analyses found matching your criteria. Run an analysis from the Single Analysis page to get started.")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Analyze AAPL", use_container_width=True):
                st.session_state.ticker = "AAPL"
                st.switch_page("pages/1_Single_Analysis.py")
        with col2:
            if st.button("Analyze MSFT", use_container_width=True):
                st.session_state.ticker = "MSFT"
                st.switch_page("pages/1_Single_Analysis.py")
        with col3:
            if st.button("Analyze NVDA", use_container_width=True):
                st.session_state.ticker = "NVDA"
                st.switch_page("pages/1_Single_Analysis.py")
    else:
        st.markdown(f"### Found {len(analyses)} Analyses")

        # Group by ticker option
        group_by_ticker = st.checkbox("Group by Ticker", value=False)

        if group_by_ticker:
            # Group analyses by ticker
            grouped = {}
            for analysis in analyses:
                if analysis.ticker not in grouped:
                    grouped[analysis.ticker] = []
                grouped[analysis.ticker].append(analysis)

            for ticker, ticker_analyses in grouped.items():
                with st.expander(f"{ticker} ({len(ticker_analyses)} analyses)", expanded=False):
                    for i, analysis in enumerate(ticker_analyses):
                        render_analysis_history_card(
                            analysis_id=analysis.id,
                            ticker=analysis.ticker,
                            company_name=analysis.company_name,
                            signal=analysis.signal,
                            analysis_date=analysis.analysis_date,
                            analysis_mode=analysis.analysis_mode,
                            show_actions=True,
                            key_prefix=f"grouped_{ticker}_{i}_"
                        )
        else:
            # Flat list
            for i, analysis in enumerate(analyses):
                render_analysis_history_card(
                    analysis_id=analysis.id,
                    ticker=analysis.ticker,
                    company_name=analysis.company_name,
                    signal=analysis.signal,
                    analysis_date=analysis.analysis_date,
                    analysis_mode=analysis.analysis_mode,
                    show_actions=True,
                    key_prefix=f"list_{i}_"
                )

    # Unique tickers summary
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Analyzed Tickers")
        unique_tickers = history_storage.get_unique_tickers()
        if unique_tickers:
            st.markdown(f"**{len(unique_tickers)}** unique tickers")
            st.text(", ".join(unique_tickers[:20]))
            if len(unique_tickers) > 20:
                st.text(f"... and {len(unique_tickers) - 20} more")
        else:
            st.info("No analyses yet")


if __name__ == "__main__":
    main()
