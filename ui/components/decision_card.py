"""
Decision Card Component
Displays BUY/SELL/HOLD decision with color coding and formatting.
"""

import streamlit as st
import re
from typing import Optional
import html


def format_decision_text(text: str) -> str:
    """
    Format decision text by converting markers to styled badges.

    Args:
        text: Raw decision text with markers

    Returns:
        HTML formatted text
    """
    # Escape HTML first
    formatted = html.escape(text)

    # Replace status markers with styled badges
    badge_styles = {
        '[PASS]': '<span style="background:#28a745;color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;font-weight:600;">✓ PASS</span>',
        '[FAIL]': '<span style="background:#dc3545;color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;font-weight:600;">✗ FAIL</span>',
        '[N/A]': '<span style="background:#6c757d;color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;">N/A</span>',
        '[NO]': '<span style="background:#6c757d;color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;">NO</span>',
        '[YES]': '<span style="background:#28a745;color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;">YES</span>',
        '[DATA MISSING]': '<span style="background:#ffc107;color:#333;padding:2px 8px;border-radius:4px;font-size:0.85em;">⚠ DATA MISSING</span>',
    }

    for marker, badge in badge_styles.items():
        formatted = formatted.replace(html.escape(marker), badge)

    # Format section headers
    section_headers = [
        'FINAL DECISION:',
        'THESIS COMPLIANCE SUMMARY',
        'Hard Fail Checks:',
        'Hard Fail Result:',
        'Qualitative Risk Tally',
        'Decision Framework Applied:',
        '=== DECISION LOGIC ===',
    ]

    for header in section_headers:
        escaped_header = html.escape(header)
        if escaped_header in formatted:
            formatted = formatted.replace(
                escaped_header,
                f'<strong style="color:#333;font-size:1.1em;">{escaped_header}</strong>'
            )

    # Convert newlines to <br> tags
    formatted = formatted.replace('\n', '<br>')

    # Format bullet points
    formatted = re.sub(r'•\s*', '<br>• ', formatted)
    formatted = re.sub(r'-\s+(?=\[)', ' → ', formatted)

    return formatted


def parse_decision_sections(text: str) -> dict:
    """
    Parse decision text into structured sections.

    Args:
        text: Raw decision text

    Returns:
        Dictionary with parsed sections
    """
    sections = {
        'decision': None,
        'hard_fails': [],
        'hard_fail_result': None,
        'qualitative_risks': [],
        'decision_logic': {}
    }

    # Extract final decision
    decision_match = re.search(r'FINAL DECISION:\s*(\w+)', text)
    if decision_match:
        sections['decision'] = decision_match.group(1)

    # Extract hard fail checks
    hard_fail_pattern = r'•\s*([^:]+):\s*\[([^\]]+)\].*?-\s*\[([^\]]+)\]'
    for match in re.finditer(hard_fail_pattern, text):
        sections['hard_fails'].append({
            'name': match.group(1).strip(),
            'value': match.group(2),
            'status': match.group(3)
        })

    # Extract hard fail result
    fail_result_match = re.search(r'Hard Fail Result:\s*(\w+)(?:\s+on:\s*\[([^\]]+)\])?', text)
    if fail_result_match:
        sections['hard_fail_result'] = {
            'result': fail_result_match.group(1),
            'reason': fail_result_match.group(2) if fail_result_match.group(2) else None
        }

    # Extract decision logic
    logic_patterns = {
        'zone': r'ZONE:\s*\[([^\]]+)\]',
        'default_decision': r'Default Decision:\s*\[([^\]]+)\]',
        'actual_decision': r'Actual Decision:\s*\[([^\]]+)\]',
        'data_vacuum': r'Data Vacuum Penalty Applied:\s*\[([^\]]+)\]',
        'override': r'Override:\s*\[([^\]]+)\]'
    }

    for key, pattern in logic_patterns.items():
        match = re.search(pattern, text)
        if match:
            sections['decision_logic'][key] = match.group(1)

    return sections


def extract_decision_type(decision_text) -> str:
    """
    Extract decision type (BUY/SELL/HOLD) from decision text.

    Args:
        decision_text: Full decision text (string or list of strings)

    Returns:
        Decision type: 'BUY', 'SELL', 'HOLD', or 'UNKNOWN'
    """
    # Handle list input by joining into a single string
    if isinstance(decision_text, list):
        decision_text = ' '.join(str(item) for item in decision_text)
    elif not isinstance(decision_text, str):
        decision_text = str(decision_text)

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
    decision_text,
    ticker: Optional[str] = None,
    show_icon: bool = True
) -> None:
    """
    Render a decision card with color coding and structured formatting.

    Args:
        decision_text: Full decision text from analysis (string or list of strings)
        ticker: Optional ticker symbol to display
        show_icon: Whether to show decision icon
    """
    # Normalize decision_text to string if it's a list
    if isinstance(decision_text, list):
        decision_text = '\n'.join(str(item) for item in decision_text)
    elif not isinstance(decision_text, str):
        decision_text = str(decision_text)

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

    # Parse sections for structured display
    sections = parse_decision_sections(decision_text)

    # Header
    header_text = f"{ticker} - " if ticker else ""
    header_text += f"{'Trading Decision' if decision_type != 'UNKNOWN' else 'Analysis Result'}"

    # Render main decision header
    st.markdown(f"""
    <div style="
        background-color: {bg_color};
        border-left: 8px solid {border_color};
        border-radius: 10px;
        padding: 1.5rem 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    ">
        <div style="display: flex; align-items: center;">
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
    </div>
    """, unsafe_allow_html=True)

    # Render structured sections if parsed successfully
    if sections['hard_fails']:
        _render_compliance_checks(sections, text_color)
    else:
        # Fallback: render formatted text in expander
        with st.expander("📋 View Full Analysis Details", expanded=False):
            formatted_text = format_decision_text(decision_text)
            st.markdown(f"""
            <div style="
                background-color: #f8f9fa;
                padding: 1.5rem;
                border-radius: 8px;
                line-height: 1.8;
                font-size: 0.95rem;
            ">
                {formatted_text}
            </div>
            """, unsafe_allow_html=True)


def _render_compliance_checks(sections: dict, text_color: str) -> None:
    """Render the compliance check results in a structured format."""

    # Hard Fail Result summary
    if sections['hard_fail_result']:
        result = sections['hard_fail_result']
        is_fail = result['result'] == 'FAIL'
        result_color = '#dc3545' if is_fail else '#28a745'
        result_icon = '❌' if is_fail else '✅'

        fail_reason = f" on {result['reason']}" if result.get('reason') else ""

        st.markdown(f"""
        <div style="
            background: {'#fff5f5' if is_fail else '#f0fff4'};
            border: 2px solid {result_color};
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin: 1rem 0;
            display: flex;
            align-items: center;
            gap: 1rem;
        ">
            <span style="font-size: 1.5rem;">{result_icon}</span>
            <div>
                <strong style="color: {result_color}; font-size: 1.1rem;">
                    Hard Fail Check: {result['result']}{fail_reason}
                </strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Compliance checks table
    with st.expander("📊 Thesis Compliance Details", expanded=True):
        if sections['hard_fails']:
            # Create a nice table for hard fail checks
            st.markdown("#### Hard Fail Checks")

            for check in sections['hard_fails']:
                status = check['status']
                status_color = '#28a745' if status == 'PASS' else '#dc3545' if status == 'FAIL' else '#6c757d'
                status_bg = '#d4edda' if status == 'PASS' else '#f8d7da' if status == 'FAIL' else '#e9ecef'
                status_icon = '✓' if status == 'PASS' else '✗' if status == 'FAIL' else '—'

                value_display = check['value']
                if 'DATA MISSING' in value_display:
                    value_display = '<span style="color:#856404;">⚠ Data Missing</span>'

                st.markdown(f"""
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 0.75rem 1rem;
                    margin: 0.25rem 0;
                    background: #fff;
                    border-radius: 6px;
                    border: 1px solid #e0e0e0;
                ">
                    <div style="flex: 1;">
                        <strong>{check['name']}</strong>
                        <span style="color: #666; margin-left: 0.5rem; font-size: 0.9rem;">
                            {value_display}
                        </span>
                    </div>
                    <span style="
                        background: {status_bg};
                        color: {status_color};
                        padding: 4px 12px;
                        border-radius: 4px;
                        font-weight: 600;
                        font-size: 0.85rem;
                    ">
                        {status_icon} {status}
                    </span>
                </div>
                """, unsafe_allow_html=True)

        # Decision logic section
        if sections['decision_logic']:
            st.markdown("#### Decision Logic")
            logic = sections['decision_logic']

            cols = st.columns(5)
            logic_items = [
                ('Zone', logic.get('zone', 'N/A')),
                ('Default', logic.get('default_decision', 'N/A')),
                ('Actual', logic.get('actual_decision', 'N/A')),
                ('Data Vacuum', logic.get('data_vacuum', 'NO')),
                ('Override', logic.get('override', 'NO')),
            ]

            for col, (label, value) in zip(cols, logic_items):
                with col:
                    value_color = '#333'
                    if value in ('BUY', 'YES'):
                        value_color = '#28a745'
                    elif value in ('SELL', 'FAIL'):
                        value_color = '#dc3545'
                    elif value in ('HOLD',):
                        value_color = '#ffc107'

                    st.markdown(f"""
                    <div style="text-align: center; padding: 0.5rem;">
                        <div style="font-size: 0.8rem; color: #666; margin-bottom: 0.25rem;">{label}</div>
                        <div style="font-size: 1rem; font-weight: 600; color: {value_color};">{value}</div>
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
