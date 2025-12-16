"""
Decision Card Component
Displays BUY/SELL/HOLD decision with color coding and formatting.
"""

import streamlit as st
import re
from typing import Optional


def extract_decision_type(decision_text: str) -> str:
    """
    Extract decision type (BUY/SELL/HOLD) from decision text.

    Args:
        decision_text: Full decision text

    Returns:
        Decision type: 'BUY', 'SELL', 'HOLD', or 'UNKNOWN'
    """
    decision_upper = decision_text.upper()

    # Check for BUY signals
    buy_keywords = ['BUY', 'STRONG BUY', 'PURCHASE', 'ACCUMULATE', 'LONG']
    for keyword in buy_keywords:
        if keyword in decision_upper:
            return 'BUY'

    # Check for SELL signals
    sell_keywords = ['SELL', 'STRONG SELL', 'SHORT', 'REDUCE', 'EXIT']
    for keyword in sell_keywords:
        if keyword in decision_upper:
            return 'SELL'

    # Check for HOLD signals
    hold_keywords = ['HOLD', 'NEUTRAL', 'WAIT', 'MONITOR', 'WATCH']
    for keyword in hold_keywords:
        if keyword in decision_upper:
            return 'HOLD'

    return 'UNKNOWN'


def get_decision_color(decision_type: str) -> tuple:
    """
    Get color scheme for decision type.

    Args:
        decision_type: 'BUY', 'SELL', 'HOLD', or 'UNKNOWN'

    Returns:
        Tuple of (background_color, text_color, border_color)
    """
    colors = {
        'BUY': ('#d4edda', '#155724', '#28a745'),      # Green
        'SELL': ('#f8d7da', '#721c24', '#dc3545'),     # Red
        'HOLD': ('#fff3cd', '#856404', '#ffc107'),     # Yellow
        'UNKNOWN': ('#e2e3e5', '#383d41', '#6c757d')   # Gray
    }

    return colors.get(decision_type, colors['UNKNOWN'])


def render_decision_card(
    decision_text: str,
    ticker: Optional[str] = None,
    show_icon: bool = True
) -> None:
    """
    Render a decision card with color coding.

    Args:
        decision_text: Full decision text from analysis
        ticker: Optional ticker symbol to display
        show_icon: Whether to show decision icon
    """
    # Extract decision type
    decision_type = extract_decision_type(decision_text)
    bg_color, text_color, border_color = get_decision_color(decision_type)

    # Decision icons
    icons = {
        'BUY': '📈',
        'SELL': '📉',
        'HOLD': '⏸️',
        'UNKNOWN': '❓'
    }

    icon = icons.get(decision_type, '❓')

    # Header
    header_text = f"{ticker} - " if ticker else ""
    header_text += f"{'Trading Decision' if decision_type != 'UNKNOWN' else 'Analysis Result'}"

    # Render card
    st.markdown(f"""
    <div style="
        background-color: {bg_color};
        border-left: 8px solid {border_color};
        border-radius: 10px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    ">
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            {f'<span style="font-size: 3rem; margin-right: 1rem;">{icon}</span>' if show_icon else ''}
            <div>
                <h2 style="color: {text_color}; margin: 0; font-size: 2.5rem; font-weight: bold;">
                    {decision_type}
                </h2>
                <p style="color: {text_color}; margin: 0; font-size: 1rem; opacity: 0.8;">
                    {header_text}
                </p>
            </div>
        </div>
        <div style="
            background-color: rgba(255, 255, 255, 0.5);
            padding: 1.5rem;
            border-radius: 8px;
            color: {text_color};
            line-height: 1.6;
        ">
            {decision_text}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_decision_summary(
    decision_type: str,
    confidence: Optional[float] = None,
    risk_level: Optional[str] = None,
    time_horizon: Optional[str] = None
) -> None:
    """
    Render a compact decision summary with key metrics.

    Args:
        decision_type: 'BUY', 'SELL', or 'HOLD'
        confidence: Confidence level (0-100)
        risk_level: Risk assessment ('Low', 'Medium', 'High')
        time_horizon: Recommended time horizon
    """
    bg_color, text_color, border_color = get_decision_color(decision_type)

    # Build summary HTML
    summary_html = f"""
    <div style="
        background: linear-gradient(135deg, {bg_color} 0%, {bg_color}dd 100%);
        border: 2px solid {border_color};
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="flex: 1;">
                <h3 style="color: {text_color}; margin: 0 0 0.5rem 0;">
                    Decision: <strong>{decision_type}</strong>
                </h3>
            </div>
    """

    # Add optional metrics
    metrics = []

    if confidence is not None:
        confidence_color = '#28a745' if confidence >= 70 else '#ffc107' if confidence >= 50 else '#dc3545'
        metrics.append(f"""
            <div style="text-align: center; padding: 0 1rem;">
                <div style="font-size: 1.5rem; color: {confidence_color}; font-weight: bold;">
                    {confidence:.0f}%
                </div>
                <div style="font-size: 0.8rem; color: {text_color}; opacity: 0.8;">
                    Confidence
                </div>
            </div>
        """)

    if risk_level:
        risk_colors = {
            'Low': '#28a745',
            'Medium': '#ffc107',
            'High': '#dc3545'
        }
        risk_color = risk_colors.get(risk_level, '#6c757d')
        metrics.append(f"""
            <div style="text-align: center; padding: 0 1rem;">
                <div style="font-size: 1.5rem; color: {risk_color}; font-weight: bold;">
                    {risk_level}
                </div>
                <div style="font-size: 0.8rem; color: {text_color}; opacity: 0.8;">
                    Risk Level
                </div>
            </div>
        """)

    if time_horizon:
        metrics.append(f"""
            <div style="text-align: center; padding: 0 1rem;">
                <div style="font-size: 1.5rem; color: {text_color}; font-weight: bold;">
                    {time_horizon}
                </div>
                <div style="font-size: 0.8rem; color: {text_color}; opacity: 0.8;">
                    Time Horizon
                </div>
            </div>
        """)

    if metrics:
        summary_html += '<div style="display: flex; gap: 1rem; border-left: 2px solid ' + border_color + ';">'
        summary_html += ''.join(metrics)
        summary_html += '</div>'

    summary_html += """
        </div>
    </div>
    """

    st.markdown(summary_html, unsafe_allow_html=True)


def render_signal_indicator(
    signal: str,
    strength: int,
    label: str = "Signal"
) -> None:
    """
    Render a signal strength indicator.

    Args:
        signal: 'bullish', 'bearish', or 'neutral'
        strength: Signal strength (1-5)
        label: Signal label
    """
    # Map signal to colors
    signal_colors = {
        'bullish': '#28a745',
        'bearish': '#dc3545',
        'neutral': '#ffc107'
    }

    color = signal_colors.get(signal.lower(), '#6c757d')

    # Create strength bars
    bars_html = ""
    for i in range(5):
        opacity = 1.0 if i < strength else 0.2
        bars_html += f"""
        <div style="
            width: 20%;
            height: 30px;
            background-color: {color};
            opacity: {opacity};
            border-radius: 4px;
        "></div>
        """

    st.markdown(f"""
    <div style="margin: 1rem 0;">
        <div style="margin-bottom: 0.5rem; font-weight: 600; color: #333;">
            {label}: <span style="color: {color}; text-transform: uppercase;">{signal}</span>
        </div>
        <div style="display: flex; gap: 5px;">
            {bars_html}
        </div>
    </div>
    """, unsafe_allow_html=True)
