"""
UI Utilities
Helper functions for the Streamlit UI.
"""

import streamlit as st
import yfinance as yf
from datetime import datetime
from typing import Optional, Dict, Any
import re


def format_currency(value: float, currency: str = "USD") -> str:
    """
    Format number as currency.

    Args:
        value: Numeric value
        currency: Currency code (default: USD)

    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"

    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CNY': '¥',
        'HKD': 'HK$'
    }

    symbol = symbols.get(currency, currency + ' ')

    if abs(value) >= 1_000_000_000:
        return f"{symbol}{value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{symbol}{value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{symbol}{value / 1_000:.2f}K"
    else:
        return f"{symbol}{value:.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format number as percentage.

    Args:
        value: Numeric value (0.15 for 15%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"

    # Handle both decimal (0.15) and percentage (15) inputs
    if abs(value) <= 1.0:
        value = value * 100

    return f"{value:.{decimals}f}%"


def format_number(value: float, decimals: int = 2, suffix: str = "") -> str:
    """
    Format number with thousands separator.

    Args:
        value: Numeric value
        decimals: Number of decimal places
        suffix: Optional suffix (e.g., 'M', 'K')

    Returns:
        Formatted number string
    """
    if value is None:
        return "N/A"

    formatted = f"{value:,.{decimals}f}"
    return formatted + suffix if suffix else formatted


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format timestamp for filenames.

    Args:
        dt: Datetime object (default: now)

    Returns:
        Formatted timestamp string (YYYYMMDD_HHMMSS)
    """
    if dt is None:
        dt = datetime.now()

    return dt.strftime("%Y%m%d_%H%M%S")


def format_date(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d") -> str:
    """
    Format date for display.

    Args:
        dt: Datetime object (default: now)
        format_str: Format string

    Returns:
        Formatted date string
    """
    if dt is None:
        dt = datetime.now()

    return dt.strftime(format_str)


def validate_ticker(ticker: str) -> Dict[str, Any]:
    """
    Validate ticker symbol.

    Args:
        ticker: Ticker symbol

    Returns:
        Dict with validation results
    """
    if not ticker:
        return {
            "valid": False,
            "message": "Please enter a ticker symbol"
        }

    ticker = ticker.upper().strip()

    # Basic format validation
    if not ticker.replace('.', '').replace('-', '').isalnum():
        return {
            "valid": False,
            "message": "Invalid ticker format"
        }

    try:
        # Try to fetch basic info
        stock = yf.Ticker(ticker)
        info = stock.info

        # Check if ticker exists
        if not info or 'symbol' not in info:
            return {
                "valid": False,
                "message": f"Ticker {ticker} not found"
            }

        return {
            "valid": True,
            "message": "Valid ticker",
            "name": info.get('longName', info.get('shortName', ticker)),
            "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A')
        }

    except Exception as e:
        return {
            "valid": False,
            "message": f"Error validating ticker: {str(e)}"
        }


def get_company_info(ticker: str) -> Dict[str, Any]:
    """
    Get company information for a ticker.

    Args:
        ticker: Ticker symbol

    Returns:
        Dict with company information
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            'name': info.get('longName', info.get('shortName', ticker)),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 0),
            'currency': info.get('currency', 'USD'),
            'exchange': info.get('exchange', 'N/A'),
            'website': info.get('website', ''),
            'description': info.get('longBusinessSummary', '')
        }

    except Exception as e:
        return {
            'name': ticker,
            'error': str(e)
        }


def extract_signal_from_text(text: str) -> str:
    """
    Extract trading signal (BUY/SELL/HOLD) from text.

    Args:
        text: Analysis text

    Returns:
        Signal type: 'BUY', 'SELL', 'HOLD', or 'UNKNOWN'
    """
    text_upper = text.upper()

    # Check for BUY signals
    buy_keywords = ['BUY', 'STRONG BUY', 'PURCHASE', 'ACCUMULATE', 'LONG', 'BULLISH']
    for keyword in buy_keywords:
        if keyword in text_upper:
            return 'BUY'

    # Check for SELL signals
    sell_keywords = ['SELL', 'STRONG SELL', 'SHORT', 'REDUCE', 'EXIT', 'BEARISH']
    for keyword in sell_keywords:
        if keyword in text_upper:
            return 'SELL'

    # Check for HOLD signals
    hold_keywords = ['HOLD', 'NEUTRAL', 'WAIT', 'MONITOR', 'WATCH']
    for keyword in hold_keywords:
        if keyword in text_upper:
            return 'HOLD'

    return 'UNKNOWN'


def calculate_metrics(equity_curve: list) -> Dict[str, float]:
    """
    Calculate performance metrics from equity curve.

    Args:
        equity_curve: List of equity values

    Returns:
        Dict with calculated metrics
    """
    if not equity_curve or len(equity_curve) < 2:
        return {}

    import numpy as np

    # Convert to numpy array
    equity = np.array([e['equity'] if isinstance(e, dict) else e for e in equity_curve])

    # Calculate returns
    returns = np.diff(equity) / equity[:-1]

    # Total return
    total_return = (equity[-1] - equity[0]) / equity[0]

    # Sharpe ratio (assuming 252 trading days, 0% risk-free rate)
    if len(returns) > 0 and np.std(returns) > 0:
        sharpe_ratio = np.sqrt(252) * np.mean(returns) / np.std(returns)
    else:
        sharpe_ratio = 0

    # Maximum drawdown
    cumulative = np.maximum.accumulate(equity)
    drawdown = (equity - cumulative) / cumulative
    max_drawdown = np.min(drawdown)

    # Volatility (annualized)
    volatility = np.std(returns) * np.sqrt(252)

    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'volatility': volatility,
        'final_value': equity[-1]
    }


def show_info_box(message: str, type: str = "info") -> None:
    """
    Display an info box with custom styling.

    Args:
        message: Message to display
        type: Box type ('info', 'success', 'warning', 'error')
    """
    colors = {
        'info': ('#d1ecf1', '#0c5460', '#bee5eb'),
        'success': ('#d4edda', '#155724', '#c3e6cb'),
        'warning': ('#fff3cd', '#856404', '#ffeaa7'),
        'error': ('#f8d7da', '#721c24', '#f5c6cb')
    }

    bg_color, text_color, border_color = colors.get(type, colors['info'])

    st.markdown(f"""
    <div style="
        background-color: {bg_color};
        border-left: 4px solid {border_color};
        padding: 1rem;
        border-radius: 4px;
        color: {text_color};
        margin: 1rem 0;
    ">
        {message}
    </div>
    """, unsafe_allow_html=True)


def create_download_link(data: str, filename: str, label: str, mime: str = "text/plain") -> None:
    """
    Create a download button for data.

    Args:
        data: Data to download
        filename: Filename for download
        label: Button label
        mime: MIME type
    """
    st.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime=mime
    )


def get_cache_key(*args) -> str:
    """
    Generate cache key from arguments.

    Args:
        *args: Arguments to hash

    Returns:
        Cache key string
    """
    import hashlib
    content = "_".join(str(arg) for arg in args)
    return hashlib.md5(content.encode()).hexdigest()


def safe_get(dictionary: Dict, *keys, default=None) -> Any:
    """
    Safely get nested dictionary value.

    Args:
        dictionary: Source dictionary
        *keys: Nested keys
        default: Default value if key not found

    Returns:
        Value or default
    """
    for key in keys:
        if isinstance(dictionary, dict):
            dictionary = dictionary.get(key, default)
        else:
            return default
    return dictionary


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix for truncated text

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def highlight_keywords(text: str, keywords: list, color: str = "yellow") -> str:
    """
    Highlight keywords in text.

    Args:
        text: Source text
        keywords: List of keywords to highlight
        color: Highlight color

    Returns:
        HTML formatted text
    """
    for keyword in keywords:
        pattern = re.compile(f'({re.escape(keyword)})', re.IGNORECASE)
        text = pattern.sub(
            f'<mark style="background-color: {color};">\\1</mark>',
            text
        )

    return text


@st.cache_data(ttl=3600)
def fetch_stock_data(ticker: str, period: str = "1y"):
    """
    Fetch and cache stock data.

    Args:
        ticker: Ticker symbol
        period: Time period

    Returns:
        Stock data DataFrame
    """
    stock = yf.Ticker(ticker)
    return stock.history(period=period)


def init_session_state(defaults: Dict[str, Any]) -> None:
    """
    Initialize session state with default values.

    Args:
        defaults: Dict of default values
    """
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_session_state(keys: Optional[list] = None) -> None:
    """
    Clear session state keys.

    Args:
        keys: List of keys to clear (None = all)
    """
    if keys is None:
        st.session_state.clear()
    else:
        for key in keys:
            if key in st.session_state:
                del st.session_state[key]
