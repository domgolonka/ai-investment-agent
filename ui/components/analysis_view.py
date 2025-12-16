"""
Analysis View Component
Displays analysis results in expandable sections.
"""

import streamlit as st
from typing import Optional, Dict


def render_analysis_section(
    title: str,
    content: str,
    icon: str = "📊",
    expanded: bool = False,
    show_word_count: bool = True
) -> None:
    """
    Render a single analysis section with expandable content.

    Args:
        title: Section title
        content: Section content
        icon: Section icon emoji
        expanded: Whether to expand by default
        show_word_count: Whether to show word count
    """
    if not content:
        return

    # Convert content to string based on its type
    if isinstance(content, dict):
        # Handle Gemini API response format: {'type': 'text', 'text': '...'}
        if 'text' in content:
            content = content['text']
        else:
            content = str(content)
    elif isinstance(content, list):
        # Handle list of items (could be dicts or strings)
        parts = []
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                parts.append(item['text'])
            else:
                parts.append(str(item))
        content = "\n".join(parts)
    else:
        content = str(content) if content else ""

    # Calculate word count
    word_count = len(content.split())

    # Build header
    header = f"{icon} {title}"
    if show_word_count:
        header += f" ({word_count} words)"

    with st.expander(header, expanded=expanded):
        # Check for error messages
        if content.startswith("Error"):
            st.error(content)
        else:
            st.markdown(content)


def render_analysis_sections(result: Dict, expand_first: bool = True) -> None:
    """
    Render all analysis sections from result dictionary.

    Args:
        result: Analysis result dictionary
        expand_first: Whether to expand the first section
    """
    sections = [
        {
            "key": "market_report",
            "title": "Market Analysis",
            "icon": "📊",
            "description": "Technical analysis and market trends"
        },
        {
            "key": "sentiment_report",
            "title": "Sentiment Analysis",
            "icon": "💭",
            "description": "Market sentiment and social signals"
        },
        {
            "key": "news_report",
            "title": "News Analysis",
            "icon": "📰",
            "description": "Recent news and events impact"
        },
        {
            "key": "fundamentals_report",
            "title": "Fundamentals Analysis",
            "icon": "💰",
            "description": "Financial metrics and valuation"
        },
        {
            "key": "investment_plan",
            "title": "Investment Plan",
            "icon": "📋",
            "description": "Strategic investment recommendations"
        },
        {
            "key": "trader_investment_plan",
            "title": "Trading Proposal",
            "icon": "💼",
            "description": "Tactical trading strategy"
        }
    ]

    st.markdown("## Detailed Analysis")

    for idx, section in enumerate(sections):
        content = result.get(section["key"], "")
        if content:
            # Expand first section by default
            is_expanded = expand_first and idx == 0

            render_analysis_section(
                title=section["title"],
                content=content,
                icon=section["icon"],
                expanded=is_expanded
            )


def render_debate_history(result: Dict) -> None:
    """
    Render investment debate history if available.

    Args:
        result: Analysis result dictionary
    """
    if "investment_debate_state" not in result:
        return

    debate_state = result["investment_debate_state"]

    if not debate_state:
        return

    with st.expander("🎯 Investment Debate History", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📈 Bull Perspective")
            bull_history = debate_state.get("bull_history", "")
            if bull_history:
                st.markdown(bull_history)
            else:
                st.info("No bull arguments recorded")

        with col2:
            st.markdown("### 📉 Bear Perspective")
            bear_history = debate_state.get("bear_history", "")
            if bear_history:
                st.markdown(bear_history)
            else:
                st.info("No bear arguments recorded")

        st.markdown("---")
        st.markdown(f"**Debate Rounds:** {debate_state.get('count', 0)}")


def render_risk_assessment(result: Dict) -> None:
    """
    Render risk assessment debate if available.

    Args:
        result: Analysis result dictionary
    """
    if "risk_debate_state" not in result:
        return

    risk_state = result["risk_debate_state"]

    if not risk_state:
        return

    with st.expander("⚖️ Risk Assessment Debate", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### 🔴 Risky Perspective")
            risky = risk_state.get("current_risky_response", "")
            if risky:
                st.markdown(risky)
            else:
                st.info("No risky perspective recorded")

        with col2:
            st.markdown("### 🟢 Safe Perspective")
            safe = risk_state.get("current_safe_response", "")
            if safe:
                st.markdown(safe)
            else:
                st.info("No safe perspective recorded")

        with col3:
            st.markdown("### 🟡 Neutral Perspective")
            neutral = risk_state.get("current_neutral_response", "")
            if neutral:
                st.markdown(neutral)
            else:
                st.info("No neutral perspective recorded")

        st.markdown("---")
        st.markdown(f"**Discussion Rounds:** {risk_state.get('count', 0)}")


def render_red_flags(result: Dict) -> None:
    """
    Render red flags section if available.

    Args:
        result: Analysis result dictionary
    """
    red_flags = result.get("red_flags", [])

    if not red_flags:
        return

    with st.expander("⚠️ Red Flags Detected", expanded=True):
        st.warning(f"Found {len(red_flags)} potential concerns:")

        for idx, flag in enumerate(red_flags, 1):
            st.markdown(f"{idx}. {flag}")


def render_tools_called(result: Dict) -> None:
    """
    Render tools/APIs called during analysis.

    Args:
        result: Analysis result dictionary
    """
    tools = result.get("tools_called", {})

    if not tools:
        return

    with st.expander("🔧 Tools & APIs Used", expanded=False):
        st.markdown("### Data Sources")

        # Group tools by category
        categories = {
            "Market Data": [],
            "News & Sentiment": [],
            "Fundamentals": [],
            "Other": []
        }

        for tool_name, call_count in tools.items():
            tool_lower = tool_name.lower()

            if any(x in tool_lower for x in ['price', 'chart', 'technical', 'volume']):
                categories["Market Data"].append((tool_name, call_count))
            elif any(x in tool_lower for x in ['news', 'sentiment', 'social']):
                categories["News & Sentiment"].append((tool_name, call_count))
            elif any(x in tool_lower for x in ['fundamental', 'financial', 'earnings']):
                categories["Fundamentals"].append((tool_name, call_count))
            else:
                categories["Other"].append((tool_name, call_count))

        for category, items in categories.items():
            if items:
                st.markdown(f"**{category}**")
                for tool_name, count in items:
                    st.markdown(f"- {tool_name}: {count} calls")


def render_memory_stats(result: Dict, ticker: str) -> None:
    """
    Render memory statistics if available.

    Args:
        result: Analysis result dictionary
        ticker: Ticker symbol
    """
    memory_stats = result.get("memory_statistics", {})

    if not memory_stats:
        return

    with st.expander("🧠 Memory Statistics", expanded=False):
        st.markdown(f"### Agent Memory for {ticker}")

        agents = [
            ("Bull Researcher", "bull_researcher"),
            ("Bear Researcher", "bear_researcher"),
            ("Research Manager", "research_manager"),
            ("Trader", "trader"),
            ("Portfolio Manager", "portfolio_manager")
        ]

        for agent_name, key in agents:
            stats = memory_stats.get(key, {})
            if stats:
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.markdown(f"**{agent_name}**")

                with col2:
                    count = stats.get("count", 0)
                    st.markdown(f"Memories: {count}")

                with col3:
                    available = "✓" if stats.get("available") else "✗"
                    st.markdown(f"Status: {available}")


def render_complete_analysis(result: Dict, ticker: Optional[str] = None) -> None:
    """
    Render complete analysis with all sections.

    Args:
        result: Analysis result dictionary
        ticker: Optional ticker symbol
    """
    # Main analysis sections
    render_analysis_sections(result)

    # Additional sections
    st.markdown("---")
    st.markdown("## Additional Insights")

    # Debate history
    render_debate_history(result)

    # Risk assessment
    render_risk_assessment(result)

    # Red flags
    render_red_flags(result)

    # Tools and APIs
    render_tools_called(result)

    # Memory statistics
    if ticker:
        render_memory_stats(result, ticker)
