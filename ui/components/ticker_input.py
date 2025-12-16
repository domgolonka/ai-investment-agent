"""
Ticker Input Component
Provides a validated ticker input widget with autocomplete suggestions.
"""

import streamlit as st
import yfinance as yf
from typing import Optional


def get_ticker_suggestions(query: str, limit: int = 5) -> list:
    """Get ticker suggestions based on query."""
    # Common tickers for quick suggestions
    common_tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META",
        "NVDA", "TSLA", "JPM", "V", "WMT",
        "JNJ", "PG", "MA", "HD", "BAC"
    ]

    if not query:
        return common_tickers[:limit]

    query = query.upper()
    matches = [t for t in common_tickers if query in t]

    return matches[:limit] if matches else []


def validate_ticker_input(ticker: str) -> dict:
    """
    Validate ticker symbol.

    Returns:
        dict with 'valid' (bool) and 'message' (str)
    """
    if not ticker:
        return {"valid": False, "message": "Please enter a ticker symbol"}

    ticker = ticker.upper().strip()

    # Basic format validation
    if not ticker.isalnum() and '.' not in ticker:
        return {"valid": False, "message": "Invalid ticker format"}

    try:
        # Try to fetch ticker info
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info

        # Check if ticker exists
        if not info or 'symbol' not in info:
            return {"valid": False, "message": f"Ticker {ticker} not found"}

        return {
            "valid": True,
            "message": "Valid ticker",
            "name": info.get('longName', ticker)
        }

    except Exception as e:
        return {"valid": False, "message": f"Error validating ticker: {str(e)}"}


def render_ticker_input(
    label: str = "Ticker Symbol",
    default_value: str = "",
    key: Optional[str] = None
) -> str:
    """
    Render ticker input widget with validation.

    Args:
        label: Input label
        default_value: Default ticker value
        key: Streamlit widget key

    Returns:
        Validated ticker symbol or empty string
    """
    # Input field
    ticker = st.text_input(
        label,
        value=default_value,
        max_chars=10,
        help="Enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL)",
        key=key
    ).upper().strip()

    # Store in session state
    if ticker and key:
        st.session_state[key] = ticker

    # Show suggestions if input is empty or partial
    if len(ticker) <= 3:
        suggestions = get_ticker_suggestions(ticker)
        if suggestions:
            st.caption(f"Popular: {', '.join(suggestions[:5])}")

    # Validate ticker if provided
    if ticker:
        validation = validate_ticker_input(ticker)

        if validation["valid"]:
            # Show company name if available
            if "name" in validation:
                st.success(f"✓ {validation['name']}")
        else:
            st.error(validation["message"])
            return ""

    return ticker


def render_ticker_multiselect(
    label: str = "Select Tickers",
    default_values: list = None,
    key: Optional[str] = None
) -> list:
    """
    Render multi-ticker selection widget.

    Args:
        label: Input label
        default_values: Default ticker list
        key: Streamlit widget key

    Returns:
        List of validated ticker symbols
    """
    # Common tickers for selection
    common_tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META",
        "NVDA", "TSLA", "JPM", "V", "WMT",
        "JNJ", "PG", "MA", "HD", "BAC"
    ]

    selected_tickers = st.multiselect(
        label,
        options=common_tickers,
        default=default_values or [],
        help="Select one or more ticker symbols",
        key=key
    )

    # Allow custom ticker input
    custom_ticker = st.text_input(
        "Or enter custom ticker",
        max_chars=10,
        help="Enter additional ticker not in the list",
        key=f"{key}_custom" if key else None
    ).upper().strip()

    if custom_ticker and custom_ticker not in selected_tickers:
        validation = validate_ticker_input(custom_ticker)
        if validation["valid"]:
            selected_tickers.append(custom_ticker)
            st.success(f"Added {custom_ticker}")
        else:
            st.error(validation["message"])

    return selected_tickers
