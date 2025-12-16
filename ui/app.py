"""
AI Investment Agent - Streamlit Web UI
Main application entry point with navigation and welcome page.
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Page configuration
st.set_page_config(
    page_title="AI Investment Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/ai-investment-agent',
        'Report a bug': 'https://github.com/your-repo/ai-investment-agent/issues',
        'About': """
        # AI Investment Agent
        A multi-agent AI system for comprehensive investment analysis.

        **Version:** 3.1.0
        **Powered by:** Google Gemini & LangGraph
        """
    }
)

# Custom CSS for enhanced UI
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .feature-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .feature-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    .feature-description {
        color: #555;
        line-height: 1.6;
    }
    .stats-box {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    """Main application page with welcome message and overview."""

    # Header
    st.markdown('<h1 class="main-header">AI Investment Agent</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Multi-Agent AI System for Comprehensive Investment Analysis</p>',
        unsafe_allow_html=True
    )

    # Overview section
    st.markdown("---")
    st.markdown("## Welcome")

    st.markdown("""
    This sophisticated multi-agent system leverages cutting-edge AI to provide comprehensive
    investment analysis, combining fundamental research, technical analysis, sentiment tracking,
    and risk assessment to help you make informed investment decisions.
    """)

    # Feature cards
    st.markdown("## Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">📊 Single Ticker Analysis</div>
            <div class="feature-description">
                Get comprehensive analysis for individual stocks with Quick or Deep mode.
                Includes market analysis, sentiment tracking, news analysis, fundamentals,
                and actionable trading recommendations.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">📈 Portfolio Management</div>
            <div class="feature-description">
                Upload and analyze your entire portfolio. Track positions, view P&L metrics,
                and get AI-powered analysis across all holdings with comprehensive
                performance insights.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">🔬 Backtesting Engine</div>
            <div class="feature-description">
                Test your investment strategies against historical data. View detailed
                performance metrics including Sharpe ratio, maximum drawdown, win rate,
                and equity curves.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">🔍 Peer Comparison</div>
            <div class="feature-description">
                Auto-detect industry peers and compare companies across valuation, growth,
                profitability, and financial health metrics. Visualize competitive positioning
                with interactive rankings.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Quick stats
    st.markdown("---")
    st.markdown("## System Capabilities")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="stats-box">
            <h3 style="color: #667eea; margin: 0;">5+</h3>
            <p style="margin: 0; color: #666;">AI Agents</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="stats-box">
            <h3 style="color: #667eea; margin: 0;">2</h3>
            <p style="margin: 0; color: #666;">Analysis Modes</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="stats-box">
            <h3 style="color: #667eea; margin: 0;">10+</h3>
            <p style="margin: 0; color: #666;">Data Sources</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="stats-box">
            <h3 style="color: #667eea; margin: 0;">Real-time</h3>
            <p style="margin: 0; color: #666;">Market Data</p>
        </div>
        """, unsafe_allow_html=True)

    # Getting started
    st.markdown("---")
    st.markdown("## Getting Started")

    st.markdown("""
    1. **Single Analysis**: Start by analyzing a single ticker to understand the system's capabilities
    2. **Portfolio Upload**: Import your existing portfolio via CSV or Excel
    3. **Run Backtests**: Validate strategies using historical performance data
    4. **Compare Peers**: Understand competitive positioning in the market
    """)

    # Sidebar navigation info
    with st.sidebar:
        st.markdown("### Navigation")
        st.markdown("""
        Use the sidebar to navigate between different features:

        - **Single Analysis**: Analyze individual stocks
        - **Portfolio**: Manage and analyze portfolios
        - **Backtesting**: Test strategies historically
        - **Peer Comparison**: Compare with competitors
        """)

        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        **Version:** 3.1.0
        **Powered by:**
        - Google Gemini
        - LangGraph
        - yfinance
        - Streamlit
        """)

        st.markdown("---")
        st.markdown("### Support")
        st.markdown("""
        - [Documentation](https://github.com/your-repo)
        - [Report Issues](https://github.com/your-repo/issues)
        - [Community](https://discord.gg/your-server)
        """)


if __name__ == "__main__":
    main()
