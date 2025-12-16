"""
State Helpers Module - Utility functions for safely accessing and manipulating AgentState.

This module provides type-safe helper functions to reduce repeated patterns when
accessing fields from the AgentState TypedDict. All functions handle missing or
None values gracefully with sensible defaults.

Design Principles:
- Type safety with comprehensive type hints
- Defensive programming with safe defaults
- Consistent API across all helper functions
- Zero side effects (pure functions)
- Clear documentation with examples

Example Usage:
    from src.state_helpers import get_reports, get_ticker_info, is_valid_ticker_state

    # Get all analysis reports at once
    reports = get_reports(state)
    print(reports['market'])  # Market analyst report

    # Get ticker identification info
    ticker_info = get_ticker_info(state)
    print(f"Analyzing {ticker_info['ticker']} - {ticker_info['company_name']}")

    # Check if state has valid ticker info before processing
    if is_valid_ticker_state(state):
        process_analysis(state)
"""

from typing import Any, Dict, List, Optional, TypeVar, Union, overload
from typing_extensions import TypedDict

# Import state types from agents module
from src.agents import AgentState, InvestDebateState, RiskDebateState


# Generic type variable for default values
T = TypeVar('T')


# --- Core Access Functions ---


@overload
def get_safe_field(state: AgentState, field: str) -> str: ...


@overload
def get_safe_field(state: AgentState, field: str, default: T) -> T: ...


def get_safe_field(state: AgentState, field: str, default: Any = '') -> Any:
    """
    Safely get a field from state with a default value.

    Handles missing keys, None values, and provides type-safe access
    to AgentState fields. Uses empty string as default for string fields
    to maintain compatibility with string concatenation operations.

    Args:
        state: The AgentState dictionary to read from.
        field: The field name to access.
        default: The default value to return if field is missing or None.
                 Defaults to empty string for backward compatibility.

    Returns:
        The field value if present and not None, otherwise the default value.

    Examples:
        >>> state = {'market_report': 'Strong bullish signals'}
        >>> get_safe_field(state, 'market_report')
        'Strong bullish signals'
        >>> get_safe_field(state, 'missing_field')
        ''
        >>> get_safe_field(state, 'missing_field', 'N/A')
        'N/A'
        >>> get_safe_field(state, 'count', 0)
        0
    """
    value = state.get(field)
    if value is None:
        return default
    return value


def get_safe_field_or_none(state: AgentState, field: str) -> Optional[Any]:
    """
    Get a field from state, returning None if missing.

    Unlike get_safe_field(), this function distinguishes between
    missing keys and explicitly None values by returning None for both.
    Useful when you need to check for field presence explicitly.

    Args:
        state: The AgentState dictionary to read from.
        field: The field name to access.

    Returns:
        The field value if present, None otherwise.

    Examples:
        >>> state = {'market_report': 'data', 'empty_field': None}
        >>> get_safe_field_or_none(state, 'market_report')
        'data'
        >>> get_safe_field_or_none(state, 'missing') is None
        True
    """
    return state.get(field)


# --- Report Access Functions ---


def get_reports(state: AgentState) -> Dict[str, str]:
    """
    Get all analysis reports from state as a structured dictionary.

    Extracts the four main analyst reports from state with safe defaults.
    Useful for aggregating all analysis data for synthesis or display.

    Args:
        state: The AgentState containing analyst reports.

    Returns:
        Dictionary with keys 'market', 'sentiment', 'news', 'fundamentals',
        each containing the respective report string or empty string if missing.

    Examples:
        >>> reports = get_reports(state)
        >>> print(reports['market'])
        'Bullish momentum detected...'
        >>> all_content = '\\n'.join(reports.values())
    """
    return {
        'market': get_safe_field(state, 'market_report', ''),
        'sentiment': get_safe_field(state, 'sentiment_report', ''),
        'news': get_safe_field(state, 'news_report', ''),
        'fundamentals': get_safe_field(state, 'fundamentals_report', ''),
    }


def get_all_reports_with_labels(state: AgentState) -> Dict[str, str]:
    """
    Get all reports including optional consultant review with descriptive labels.

    Extended version of get_reports() that includes the consultant cross-validation
    review if available. Labels match those used in prompt construction.

    Args:
        state: The AgentState containing analyst reports.

    Returns:
        Dictionary with descriptive keys for all available reports.

    Examples:
        >>> reports = get_all_reports_with_labels(state)
        >>> for label, content in reports.items():
        ...     print(f"=== {label} ===\\n{content}")
    """
    return {
        'MARKET ANALYST REPORT': get_safe_field(state, 'market_report', 'N/A'),
        'SENTIMENT ANALYST REPORT': get_safe_field(state, 'sentiment_report', 'N/A'),
        'NEWS ANALYST REPORT': get_safe_field(state, 'news_report', 'N/A'),
        'FUNDAMENTALS ANALYST REPORT': get_safe_field(state, 'fundamentals_report', 'N/A'),
        'CONSULTANT REVIEW': get_safe_field(state, 'consultant_review', 'N/A'),
    }


# --- Ticker Information Functions ---


def get_ticker_info(state: AgentState) -> Dict[str, str]:
    """
    Get ticker identification info from state.

    Extracts the core identification fields needed to identify the
    company being analyzed. Provides sensible defaults for display.

    Args:
        state: The AgentState containing ticker information.

    Returns:
        Dictionary with 'ticker', 'company_name', and 'trade_date' keys.

    Examples:
        >>> info = get_ticker_info(state)
        >>> print(f"Analyzing {info['ticker']} ({info['company_name']})")
        'Analyzing AAPL (Apple Inc.)'
    """
    return {
        'ticker': get_safe_field(state, 'company_of_interest', 'UNKNOWN'),
        'company_name': get_safe_field(state, 'company_name', 'Unknown Company'),
        'trade_date': get_safe_field(state, 'trade_date', ''),
    }


def is_valid_ticker_state(state: AgentState) -> bool:
    """
    Check if state has valid ticker information populated.

    Validates that the essential ticker identification fields are present
    and contain meaningful values (not placeholders or empty).

    Args:
        state: The AgentState to validate.

    Returns:
        True if ticker info is valid and populated, False otherwise.

    Examples:
        >>> state = {'company_of_interest': 'AAPL', 'company_name': 'Apple Inc.'}
        >>> is_valid_ticker_state(state)
        True
        >>> state = {'company_of_interest': 'UNKNOWN'}
        >>> is_valid_ticker_state(state)
        False
    """
    ticker = get_safe_field(state, 'company_of_interest', '')
    company_name = get_safe_field(state, 'company_name', '')

    # Check ticker is present and not a placeholder
    if not ticker or ticker == 'UNKNOWN':
        return False

    # Check company name is present and not a placeholder
    if not company_name or company_name == 'Unknown Company':
        return False

    return True


# --- Debate State Functions ---


def get_investment_debate_state(state: AgentState) -> InvestDebateState:
    """
    Safely get InvestDebateState from AgentState with defaults.

    Returns a fully initialized InvestDebateState dictionary with all
    required fields. If the state field is missing or None, returns
    an empty initialized state.

    Args:
        state: The AgentState containing investment_debate_state.

    Returns:
        InvestDebateState dictionary with all fields guaranteed present.

    Examples:
        >>> debate = get_investment_debate_state(state)
        >>> print(f"Round {debate['count']}: {debate['history']}")
    """
    debate_state = state.get('investment_debate_state')

    if debate_state is None or not isinstance(debate_state, dict):
        return _create_empty_invest_debate_state()

    # Ensure all required fields are present with defaults
    return {
        'bull_history': debate_state.get('bull_history', ''),
        'bear_history': debate_state.get('bear_history', ''),
        'history': debate_state.get('history', ''),
        'current_response': debate_state.get('current_response', ''),
        'judge_decision': debate_state.get('judge_decision', ''),
        'count': debate_state.get('count', 0),
    }


def get_risk_debate_state(state: AgentState) -> RiskDebateState:
    """
    Safely get RiskDebateState from AgentState with defaults.

    Returns a fully initialized RiskDebateState dictionary with all
    required fields. If the state field is missing or None, returns
    an empty initialized state.

    Args:
        state: The AgentState containing risk_debate_state.

    Returns:
        RiskDebateState dictionary with all fields guaranteed present.

    Examples:
        >>> risk = get_risk_debate_state(state)
        >>> print(f"Risk assessment round {risk['count']}")
    """
    risk_state = state.get('risk_debate_state')

    if risk_state is None or not isinstance(risk_state, dict):
        return _create_empty_risk_debate_state()

    # Ensure all required fields are present with defaults
    return {
        'risky_history': risk_state.get('risky_history', ''),
        'safe_history': risk_state.get('safe_history', ''),
        'neutral_history': risk_state.get('neutral_history', ''),
        'history': risk_state.get('history', ''),
        'latest_speaker': risk_state.get('latest_speaker', ''),
        'current_risky_response': risk_state.get('current_risky_response', ''),
        'current_safe_response': risk_state.get('current_safe_response', ''),
        'current_neutral_response': risk_state.get('current_neutral_response', ''),
        'judge_decision': risk_state.get('judge_decision', ''),
        'count': risk_state.get('count', 0),
    }


def _create_empty_invest_debate_state() -> InvestDebateState:
    """
    Create an empty initialized InvestDebateState.

    Internal helper function to create a properly initialized
    InvestDebateState with all required fields set to defaults.

    Returns:
        Empty InvestDebateState dictionary.
    """
    return {
        'bull_history': '',
        'bear_history': '',
        'history': '',
        'current_response': '',
        'judge_decision': '',
        'count': 0,
    }


def _create_empty_risk_debate_state() -> RiskDebateState:
    """
    Create an empty initialized RiskDebateState.

    Internal helper function to create a properly initialized
    RiskDebateState with all required fields set to defaults.

    Returns:
        Empty RiskDebateState dictionary.
    """
    return {
        'risky_history': '',
        'safe_history': '',
        'neutral_history': '',
        'history': '',
        'latest_speaker': '',
        'current_risky_response': '',
        'current_safe_response': '',
        'current_neutral_response': '',
        'judge_decision': '',
        'count': 0,
    }


# --- Context Building Functions ---


def get_debate_context(state: AgentState) -> str:
    """
    Build context string from all reports for debate.

    Combines all analyst reports and debate history into a single
    formatted string suitable for injection into debate prompts.

    Args:
        state: The AgentState containing reports and debate state.

    Returns:
        Formatted string containing all context for debate agents.

    Examples:
        >>> context = get_debate_context(state)
        >>> prompt = f"{system_instruction}\\n\\n{context}\\n\\nProvide your argument."
    """
    reports = get_reports(state)
    debate = get_investment_debate_state(state)

    sections = [
        f"MARKET ANALYSIS:\n{reports['market']}" if reports['market'] else None,
        f"SENTIMENT ANALYSIS:\n{reports['sentiment']}" if reports['sentiment'] else None,
        f"NEWS ANALYSIS:\n{reports['news']}" if reports['news'] else None,
        f"FUNDAMENTALS ANALYSIS:\n{reports['fundamentals']}" if reports['fundamentals'] else None,
        f"DEBATE HISTORY:\n{debate['history']}" if debate['history'] else None,
    ]

    # Filter out None sections and join with double newlines
    return '\n\n'.join(section for section in sections if section)


def format_analysis_context(state: AgentState) -> str:
    """
    Format all reports for use in prompts with standardized headers.

    Creates a comprehensive formatted context string that includes all
    analyst reports, debate histories, and synthesis outputs. Uses
    consistent formatting that matches the pattern used throughout
    the agent codebase.

    Args:
        state: The AgentState containing all analysis data.

    Returns:
        Fully formatted context string ready for prompt injection.

    Examples:
        >>> context = format_analysis_context(state)
        >>> final_prompt = f"{system_message}\\n\\n{context}\\n\\nMake final decision."
    """
    # Get all components
    ticker_info = get_ticker_info(state)
    reports = get_all_reports_with_labels(state)
    invest_debate = get_investment_debate_state(state)
    risk_debate = get_risk_debate_state(state)

    # Build header
    header = f"""=== ANALYSIS CONTEXT ===
Ticker: {ticker_info['ticker']}
Company: {ticker_info['company_name']}
Trade Date: {ticker_info['trade_date'] or 'Not specified'}
"""

    # Build report sections
    report_sections = []
    for label, content in reports.items():
        if content and content != 'N/A':
            report_sections.append(f"=== {label} ===\n{content}")

    # Add debate contexts if available
    if invest_debate['history']:
        bull_bear_section = f"""=== INVESTMENT DEBATE ===
Bull Arguments:
{invest_debate['bull_history'] or 'N/A'}

Bear Arguments:
{invest_debate['bear_history'] or 'N/A'}

Full Debate History:
{invest_debate['history']}
"""
        report_sections.append(bull_bear_section)

    if risk_debate['history']:
        risk_section = f"""=== RISK ASSESSMENT DEBATE ===
{risk_debate['history']}
"""
        report_sections.append(risk_section)

    # Add investment plan if available
    investment_plan = get_safe_field(state, 'investment_plan', '')
    if investment_plan:
        report_sections.append(f"=== INVESTMENT PLAN ===\n{investment_plan}")

    # Add trader plan if available
    trader_plan = get_safe_field(state, 'trader_investment_plan', '')
    if trader_plan:
        report_sections.append(f"=== TRADER INVESTMENT PLAN ===\n{trader_plan}")

    return header + '\n\n' + '\n\n'.join(report_sections)


def format_reports_for_synthesis(state: AgentState) -> str:
    """
    Format reports specifically for research manager synthesis.

    Creates a condensed format optimized for the research manager
    agent to synthesize analyst reports and debate outcomes.

    Args:
        state: The AgentState containing analyst reports and debate.

    Returns:
        Formatted string optimized for synthesis prompts.
    """
    reports = get_reports(state)
    debate = get_investment_debate_state(state)

    return f"""MARKET ANALYST REPORT:
{reports['market'] or 'N/A'}

SENTIMENT ANALYST REPORT:
{reports['sentiment'] or 'N/A'}

NEWS ANALYST REPORT:
{reports['news'] or 'N/A'}

FUNDAMENTALS ANALYST REPORT:
{reports['fundamentals'] or 'N/A'}

BULL RESEARCHER:
{debate['bull_history'] or 'N/A'}

BEAR RESEARCHER:
{debate['bear_history'] or 'N/A'}"""


# --- State Update Functions ---


def update_state_fields(state: AgentState, **kwargs: Any) -> Dict[str, Any]:
    """
    Return dict of fields to update in state.

    Helper function to create state update dictionaries in a consistent
    manner. Filters out None values to avoid overwriting existing data
    with None unless explicitly desired.

    Args:
        state: The current AgentState (for reference, not modified).
        **kwargs: Key-value pairs of fields to update.

    Returns:
        Dictionary containing the field updates (filtered for non-None).

    Examples:
        >>> updates = update_state_fields(state, market_report='New report', count=5)
        >>> return updates  # In an agent node function
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def merge_state_updates(*updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple state update dictionaries.

    Combines multiple update dictionaries into one, with later updates
    taking precedence over earlier ones for duplicate keys.

    Args:
        *updates: Variable number of update dictionaries to merge.

    Returns:
        Single merged dictionary containing all updates.

    Examples:
        >>> update1 = {'market_report': 'data1', 'count': 1}
        >>> update2 = {'sentiment_report': 'data2', 'count': 2}
        >>> merged = merge_state_updates(update1, update2)
        >>> merged['count']
        2
    """
    result: Dict[str, Any] = {}
    for update in updates:
        if update:
            result.update(update)
    return result


# --- Red Flag and Pre-Screening Functions ---


def get_red_flags(state: AgentState) -> List[Dict[str, Any]]:
    """
    Get the list of detected red flags from state.

    Args:
        state: The AgentState containing red_flags field.

    Returns:
        List of red flag dictionaries, empty list if none detected.

    Examples:
        >>> flags = get_red_flags(state)
        >>> critical = [f for f in flags if f.get('severity') == 'CRITICAL']
    """
    flags = state.get('red_flags')
    if flags is None or not isinstance(flags, list):
        return []
    return flags


def get_pre_screening_result(state: AgentState) -> str:
    """
    Get the pre-screening result from state.

    Args:
        state: The AgentState containing pre_screening_result.

    Returns:
        'PASS', 'REJECT', or 'UNKNOWN' if not set.

    Examples:
        >>> if get_pre_screening_result(state) == 'REJECT':
        ...     skip_debate = True
    """
    result = state.get('pre_screening_result')
    if result not in ('PASS', 'REJECT'):
        return 'UNKNOWN'
    return result


def has_critical_red_flags(state: AgentState) -> bool:
    """
    Check if state contains any critical (AUTO_REJECT) red flags.

    Args:
        state: The AgentState to check.

    Returns:
        True if any critical red flags are present, False otherwise.

    Examples:
        >>> if has_critical_red_flags(state):
        ...     logger.warning("Critical financial issues detected")
    """
    flags = get_red_flags(state)
    return any(
        flag.get('severity') == 'CRITICAL' or flag.get('action') == 'AUTO_REJECT'
        for flag in flags
    )


# --- Validation Functions ---


def has_required_reports(state: AgentState, required: Optional[List[str]] = None) -> bool:
    """
    Check if state has the required analyst reports populated.

    Args:
        state: The AgentState to validate.
        required: List of report keys to check. Defaults to all four main reports.
                  Valid keys: 'market', 'sentiment', 'news', 'fundamentals'

    Returns:
        True if all required reports are present and non-empty.

    Examples:
        >>> if has_required_reports(state, ['market', 'fundamentals']):
        ...     proceed_to_debate()
    """
    if required is None:
        required = ['market', 'sentiment', 'news', 'fundamentals']

    reports = get_reports(state)

    for key in required:
        if key not in reports or not reports[key]:
            return False

    return True


def is_debate_complete(state: AgentState, min_rounds: int = 2) -> bool:
    """
    Check if the investment debate has completed enough rounds.

    Args:
        state: The AgentState containing debate state.
        min_rounds: Minimum number of debate rounds required (default 2).

    Returns:
        True if debate has completed at least min_rounds.

    Examples:
        >>> if is_debate_complete(state, min_rounds=3):
        ...     proceed_to_synthesis()
    """
    debate = get_investment_debate_state(state)
    return debate['count'] >= min_rounds


def is_risk_assessment_complete(state: AgentState, min_rounds: int = 1) -> bool:
    """
    Check if the risk assessment debate has completed.

    Args:
        state: The AgentState containing risk debate state.
        min_rounds: Minimum number of risk debate rounds required (default 1).

    Returns:
        True if risk assessment has completed at least min_rounds.
    """
    risk = get_risk_debate_state(state)
    return risk['count'] >= min_rounds


# --- Prompt Tracking Functions ---


def get_prompts_used(state: AgentState) -> Dict[str, Dict[str, str]]:
    """
    Get the prompts used tracking dictionary from state.

    Args:
        state: The AgentState containing prompts_used field.

    Returns:
        Dictionary mapping output fields to prompt metadata.

    Examples:
        >>> prompts = get_prompts_used(state)
        >>> print(prompts.get('market_report', {}).get('version'))
    """
    prompts = state.get('prompts_used')
    if prompts is None or not isinstance(prompts, dict):
        return {}
    return prompts


def get_tools_called(state: AgentState) -> Dict[str, Any]:
    """
    Get the tools called tracking dictionary from state.

    Args:
        state: The AgentState containing tools_called field.

    Returns:
        Dictionary tracking which tools have been called.

    Examples:
        >>> tools = get_tools_called(state)
        >>> if 'yahoo_finance' in tools:
        ...     print("Yahoo Finance data was fetched")
    """
    tools = state.get('tools_called')
    if tools is None or not isinstance(tools, dict):
        return {}
    return tools
