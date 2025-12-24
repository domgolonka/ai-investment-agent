"""
Watchlist View Component
Displays watchlist items with conversion and management options.
"""

import streamlit as st
from datetime import datetime
from typing import Optional, List, Callable


def get_signal_badge(signal: Optional[str]) -> str:
    """Get HTML badge for a signal."""
    if not signal:
        return ""

    colors = {
        "BUY": ("🟢", "#d4edda", "#155724"),
        "SELL": ("🔴", "#f8d7da", "#721c24"),
        "HOLD": ("🟡", "#fff3cd", "#856404"),
    }

    emoji, bg, color = colors.get(signal.upper(), ("⚪", "#e2e3e5", "#383d41"))

    return f'''<span style="
        background: {bg};
        color: {color};
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
    ">{emoji} {signal}</span>'''


def render_watchlist_item(
    item,
    current_price: Optional[float] = None,
    on_convert: Optional[Callable] = None,
    on_remove: Optional[Callable] = None,
    key_prefix: str = ""
) -> None:
    """
    Render a single watchlist item.

    Args:
        item: WatchlistItem object
        current_price: Current market price (if available)
        on_convert: Callback for conversion to position
        on_remove: Callback for removing from watchlist
        key_prefix: Prefix for Streamlit widget keys
    """
    signal_badge = get_signal_badge(item.latest_signal)

    # Price comparison
    price_comparison = ""
    if current_price and item.target_price:
        diff_pct = ((current_price - item.target_price) / item.target_price) * 100
        if diff_pct > 0:
            price_comparison = f'<span style="color: #dc3545;">↑ {diff_pct:.1f}% above target</span>'
        else:
            price_comparison = f'<span style="color: #28a745;">↓ {abs(diff_pct):.1f}% below target</span>'

    # Card
    st.markdown(f"""
        <div style="
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.5rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h4 style="margin: 0; color: #333;">{item.ticker}</h4>
                    <p style="margin: 0.25rem 0; color: #666; font-size: 0.9em;">
                        {item.company_name or ""}
                        {signal_badge}
                    </p>
                </div>
                <div style="text-align: right;">
                    {f'<div style="font-size: 1.2em; font-weight: bold;">${current_price:.2f}</div>' if current_price else ''}
                    {f'<div style="font-size: 0.85em; color: #666;">Target: ${item.target_price:.2f}</div>' if item.target_price else ''}
                    {price_comparison}
                </div>
            </div>
            <div style="margin-top: 0.5rem; color: #888; font-size: 0.85em;">
                Added: {item.added_at.strftime('%Y-%m-%d') if item.added_at else 'Unknown'}
                {f' | Analysis: {item.analysis_date.strftime("%Y-%m-%d")}' if item.analysis_date else ''}
            </div>
            {f'<div style="margin-top: 0.5rem; color: #666; font-size: 0.9em;">{item.notes}</div>' if item.notes else ''}
        </div>
    """, unsafe_allow_html=True)

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("💰 Convert to Position", key=f"{key_prefix}convert_{item.ticker}", use_container_width=True):
            if on_convert:
                on_convert(item)
            else:
                st.session_state[f"convert_watchlist_{item.ticker}"] = True
                st.rerun()

    with col2:
        if st.button("📊 Re-analyze", key=f"{key_prefix}reanalyze_{item.ticker}", use_container_width=True):
            st.session_state.ticker = item.ticker
            st.switch_page("pages/1_Single_Analysis.py")

    with col3:
        if st.button("🗑️ Remove", key=f"{key_prefix}remove_{item.ticker}", use_container_width=True):
            if on_remove:
                on_remove(item)
            else:
                st.session_state[f"remove_watchlist_{item.ticker}"] = True
                st.rerun()


def render_watchlist(
    watchlist_items: List,
    current_prices: Optional[dict] = None,
    on_convert: Optional[Callable] = None,
    on_remove: Optional[Callable] = None,
    key_prefix: str = ""
) -> None:
    """
    Render the full watchlist.

    Args:
        watchlist_items: List of WatchlistItem objects
        current_prices: Dict of ticker -> current price
        on_convert: Callback for conversion to position
        on_remove: Callback for removing from watchlist
        key_prefix: Prefix for Streamlit widget keys
    """
    if not watchlist_items:
        st.info("Your watchlist is empty. Add stocks from the Analysis History or Single Analysis page.")
        return

    current_prices = current_prices or {}

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Watchlist Items", len(watchlist_items))

    with col2:
        buy_count = sum(1 for item in watchlist_items if item.latest_signal == "BUY")
        st.metric("🟢 BUY Signals", buy_count)

    with col3:
        sell_count = sum(1 for item in watchlist_items if item.latest_signal == "SELL")
        st.metric("🔴 SELL Signals", sell_count)

    with col4:
        hold_count = sum(1 for item in watchlist_items if item.latest_signal == "HOLD")
        st.metric("🟡 HOLD Signals", hold_count)

    st.markdown("---")

    # Render items
    for i, item in enumerate(watchlist_items):
        render_watchlist_item(
            item=item,
            current_price=current_prices.get(item.ticker),
            on_convert=on_convert,
            on_remove=on_remove,
            key_prefix=f"{key_prefix}{i}_"
        )


def render_convert_modal(
    item,
    on_confirm: Callable,
    on_cancel: Callable,
    key_prefix: str = ""
) -> None:
    """
    Render a modal for converting watchlist item to position.

    Args:
        item: WatchlistItem to convert
        on_confirm: Callback with (shares, price, fees, currency) when confirmed
        on_cancel: Callback when cancelled
        key_prefix: Prefix for Streamlit widget keys
    """
    st.markdown(f"### Convert {item.ticker} to Position")

    col1, col2 = st.columns(2)

    with col1:
        shares = st.number_input(
            "Number of Shares",
            min_value=0.001,
            value=1.0,
            step=0.001,
            format="%.3f",
            key=f"{key_prefix}shares"
        )

        purchase_price = st.number_input(
            "Purchase Price ($)",
            min_value=0.01,
            value=item.target_price if item.target_price else 100.0,
            step=0.01,
            key=f"{key_prefix}price"
        )

    with col2:
        fees = st.number_input(
            "Transaction Fees ($)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            key=f"{key_prefix}fees"
        )

        currency = st.selectbox(
            "Currency",
            ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD"],
            key=f"{key_prefix}currency"
        )

    # Total cost
    total_cost = (shares * purchase_price) + fees
    st.markdown(f"**Total Cost:** ${total_cost:,.2f}")

    col_confirm, col_cancel = st.columns(2)

    with col_confirm:
        if st.button("Confirm Purchase", type="primary", use_container_width=True, key=f"{key_prefix}confirm"):
            on_confirm(shares, purchase_price, fees, currency)

    with col_cancel:
        if st.button("Cancel", use_container_width=True, key=f"{key_prefix}cancel"):
            on_cancel()
