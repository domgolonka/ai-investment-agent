"""
Single Ticker Analysis Page
Provides comprehensive analysis for individual stocks with Quick or Deep mode.
"""

import streamlit as st
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.main import run_analysis
from ui.components.ticker_input import render_ticker_input
from ui.components.decision_card import render_decision_card
from ui.components.analysis_view import render_analysis_sections
from ui.utils import validate_ticker, format_timestamp

st.set_page_config(
    page_title="Single Analysis - AI Investment Agent",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .analysis-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .progress-status {
        padding: 1rem;
        border-radius: 8px;
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)


def make_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format, handling LangChain messages."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    # Handle LangChain message objects (HumanMessage, AIMessage, etc.)
    if hasattr(obj, 'content'):
        return str(obj.content)
    # Handle datetime objects
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Fallback: convert to string
    return str(obj)


def export_to_markdown(result: dict, ticker: str) -> str:
    """Export analysis results to markdown format."""
    md_content = f"# Investment Analysis: {ticker}\n\n"
    md_content += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md_content += "---\n\n"

    def to_string(value) -> str:
        """Convert a value to string, handling dicts, lists and other types."""
        if isinstance(value, dict):
            # Handle Gemini API response format: {'type': 'text', 'text': '...'}
            if 'text' in value:
                return value['text']
            return str(value)
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict) and 'text' in item:
                    parts.append(item['text'])
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(value) if value else ""

    if result.get("final_trade_decision"):
        md_content += "## Final Decision\n\n"
        md_content += to_string(result["final_trade_decision"]) + "\n\n"

    sections = [
        ("market_report", "Market Analysis"),
        ("sentiment_report", "Sentiment Analysis"),
        ("news_report", "News Analysis"),
        ("fundamentals_report", "Fundamentals Analysis"),
        ("investment_plan", "Investment Plan"),
        ("trader_investment_plan", "Trading Proposal")
    ]

    for key, title in sections:
        if result.get(key):
            md_content += f"## {title}\n\n"
            md_content += to_string(result[key]) + "\n\n"

    return md_content


def main():
    """Main single analysis page."""

    st.markdown('<div class="analysis-header">', unsafe_allow_html=True)
    st.markdown("# 📊 Single Ticker Analysis")
    st.markdown("Comprehensive AI-powered analysis for individual stocks")
    st.markdown('</div>', unsafe_allow_html=True)

    # Sidebar configuration
    with st.sidebar:
        st.markdown("## Analysis Settings")

        # Ticker input
        ticker = render_ticker_input()

        # Mode selection
        st.markdown("### Analysis Mode")
        analysis_mode = st.radio(
            "Select analysis depth",
            ["Quick", "Deep"],
            help="Quick mode uses faster models for rapid analysis. Deep mode provides more comprehensive insights."
        )
        quick_mode = analysis_mode == "Quick"

        # Additional options
        st.markdown("### Options")
        enable_memory = st.checkbox(
            "Enable Memory",
            value=True,
            help="Use persistent memory to track analysis history"
        )

        # Run button
        run_analysis_btn = st.button(
            "🚀 Run Analysis",
            type="primary",
            use_container_width=True,
            disabled=not ticker
        )

    # Main content area
    if not ticker:
        st.info("👈 Enter a ticker symbol in the sidebar to begin analysis")

        # Show example
        st.markdown("### Example Analysis")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Analyze AAPL", use_container_width=True):
                st.session_state.ticker = "AAPL"
                st.rerun()

        with col2:
            if st.button("Analyze MSFT", use_container_width=True):
                st.session_state.ticker = "MSFT"
                st.rerun()

        with col3:
            if st.button("Analyze NVDA", use_container_width=True):
                st.session_state.ticker = "NVDA"
                st.rerun()

        return

    # Validate ticker
    if ticker:
        validation = validate_ticker(ticker)
        if not validation["valid"]:
            st.error(f"Invalid ticker: {validation['message']}")
            return

    # Run analysis
    if run_analysis_btn:
        # Store configuration in session state
        st.session_state.analysis_running = True
        st.session_state.current_ticker = ticker
        st.session_state.current_mode = analysis_mode

        # Progress indicators
        progress_container = st.container()

        with progress_container:
            st.markdown('<div class="progress-status">', unsafe_allow_html=True)
            st.markdown(f"### Analyzing {ticker} ({analysis_mode} Mode)")

            progress_bar = st.progress(0)
            status_text = st.empty()

            # Simulate progress stages
            stages = [
                (0.1, "Initializing agents..."),
                (0.2, "Fetching market data..."),
                (0.3, "Running market analysis..."),
                (0.4, "Analyzing sentiment..."),
                (0.5, "Processing news..."),
                (0.6, "Evaluating fundamentals..."),
                (0.7, "Running investment debate..."),
                (0.8, "Formulating trading plan..."),
                (0.9, "Conducting risk assessment..."),
                (1.0, "Finalizing decision..."),
            ]

            # Run async analysis
            try:
                # Update initial status
                status_text.text("Starting analysis...")

                # Create a wrapper to run async code
                async def run_async_analysis():
                    return await run_analysis(ticker, quick_mode)

                # Run the analysis
                with st.spinner("Running multi-agent analysis..."):
                    # Simulate progress updates
                    for progress, stage_text in stages:
                        progress_bar.progress(progress)
                        status_text.text(stage_text)

                    # Actually run the analysis
                    result = asyncio.run(run_async_analysis())

                    progress_bar.progress(1.0)
                    status_text.text("Analysis complete!")

                st.markdown('</div>', unsafe_allow_html=True)

                if result:
                    st.success("Analysis completed successfully!")

                    # Store result in session state
                    st.session_state.analysis_result = result
                    st.session_state.analysis_timestamp = datetime.now()

                else:
                    st.error("Analysis failed. Please check logs for details.")
                    st.session_state.analysis_running = False
                    return

            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.session_state.analysis_running = False
                return

        st.session_state.analysis_running = False

    # Display results if available
    if hasattr(st.session_state, 'analysis_result') and st.session_state.analysis_result:
        result = st.session_state.analysis_result

        st.markdown("---")

        # Decision card
        if result.get("final_trade_decision"):
            render_decision_card(
                result["final_trade_decision"],
                ticker=st.session_state.current_ticker
            )

        # Export buttons
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            # Export to Markdown
            md_content = export_to_markdown(result, st.session_state.current_ticker)
            st.download_button(
                label="📄 Export Markdown",
                data=md_content,
                file_name=f"{st.session_state.current_ticker}_analysis_{format_timestamp()}.md",
                mime="text/markdown",
                use_container_width=True
            )

        with col2:
            # Export to JSON (sanitize to handle LangChain message objects)
            json_content = json.dumps(make_json_serializable(result), indent=2)
            st.download_button(
                label="📋 Export JSON",
                data=json_content,
                file_name=f"{st.session_state.current_ticker}_analysis_{format_timestamp()}.json",
                mime="application/json",
                use_container_width=True
            )

        with col3:
            st.markdown(f"**Analysis Time:** {st.session_state.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        st.markdown("---")

        # Analysis sections
        render_analysis_sections(result)

        # Token usage summary (if available)
        if result.get("token_usage"):
            with st.expander("💰 Token Usage Summary"):
                token_stats = result["token_usage"]

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Calls", token_stats.get("total_calls", 0))

                with col2:
                    st.metric("Prompt Tokens", f"{token_stats.get('total_prompt_tokens', 0):,}")

                with col3:
                    st.metric("Completion Tokens", f"{token_stats.get('total_completion_tokens', 0):,}")

                with col4:
                    st.metric("Est. Cost", f"${token_stats.get('total_cost_usd', 0):.4f}")


if __name__ == "__main__":
    main()
