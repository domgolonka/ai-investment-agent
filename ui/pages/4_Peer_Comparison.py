"""
Peer Comparison Page
Compare companies with industry peers across multiple dimensions.
"""

import streamlit as st
import sys
from pathlib import Path
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.peers import (
    PeerFinder,
    PeerComparator,
    generate_comparison_table,
    generate_ranking_data
)
from ui.utils import validate_ticker, format_currency, format_percentage

st.set_page_config(
    page_title="Peer Comparison - AI Investment Agent",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .peer-header {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .peer-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .rank-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        color: white;
    }
    .rank-1 { background: #ffd700; color: #333; }
    .rank-2 { background: #c0c0c0; color: #333; }
    .rank-3 { background: #cd7f32; color: white; }
    .rank-other { background: #6c757d; color: white; }
    </style>
    """, unsafe_allow_html=True)


def render_comparison_radar_chart(comparison_data: dict, ticker: str):
    """Render radar chart for peer comparison."""
    categories = list(comparison_data.keys())
    values = list(comparison_data.values())

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=ticker
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)


def render_ranking_chart(ranking_data: pd.DataFrame):
    """Render horizontal bar chart for rankings."""
    fig = px.bar(
        ranking_data,
        x='score',
        y='ticker',
        orientation='h',
        color='score',
        color_continuous_scale='RdYlGn',
        labels={'score': 'Overall Score', 'ticker': 'Company'},
        title='Peer Rankings'
    )

    fig.update_layout(
        showlegend=False,
        height=400,
        xaxis_title="Score",
        yaxis_title="Company"
    )

    st.plotly_chart(fig, use_container_width=True)


async def find_peers(ticker: str):
    """Find industry peers for a given ticker."""
    finder = PeerFinder()
    peers = await finder.find_peers(ticker)
    return peers


async def compare_peers(ticker: str, peers: list):
    """Compare ticker with peers."""
    comparator = PeerComparator()
    comparison = await comparator.compare_metrics(ticker, peers)
    return comparison


def main():
    """Main peer comparison page."""

    st.markdown('<div class="peer-header">', unsafe_allow_html=True)
    st.markdown("# 🔍 Peer Comparison")
    st.markdown("Compare companies with industry peers across multiple dimensions")
    st.markdown('</div>', unsafe_allow_html=True)

    # Sidebar - Configuration
    with st.sidebar:
        st.markdown("## Comparison Settings")

        # Ticker input
        ticker = st.text_input(
            "Ticker Symbol",
            value="AAPL",
            help="Enter stock ticker to compare"
        ).upper()

        # Auto-detect peers option
        auto_detect = st.checkbox(
            "Auto-detect Peers",
            value=True,
            help="Automatically find industry peers"
        )

        # Manual peer selection
        if not auto_detect:
            st.markdown("### Manual Peer Selection")
            manual_peers = st.text_area(
                "Enter peer tickers (comma-separated)",
                value="MSFT, GOOGL, META",
                help="Enter ticker symbols separated by commas"
            )

        # Comparison dimensions
        st.markdown("### Comparison Dimensions")
        compare_valuation = st.checkbox("Valuation Metrics", value=True)
        compare_growth = st.checkbox("Growth Metrics", value=True)
        compare_profitability = st.checkbox("Profitability Metrics", value=True)
        compare_financial_health = st.checkbox("Financial Health", value=True)

        # Run comparison button
        st.markdown("---")
        run_comparison_btn = st.button(
            "🔍 Run Comparison",
            type="primary",
            use_container_width=True,
            disabled=not ticker
        )

    # Main content
    if not ticker:
        st.info("👈 Enter a ticker symbol in the sidebar to begin comparison")
        return

    # Validate ticker
    validation = validate_ticker(ticker)
    if not validation["valid"]:
        st.error(f"Invalid ticker: {validation['message']}")
        return

    # Run comparison
    if run_comparison_btn:
        with st.spinner(f"Finding peers for {ticker}..."):
            try:
                # Find peers
                if auto_detect:
                    peers = asyncio.run(find_peers(ticker))
                else:
                    # Parse manual peers
                    peers = [p.strip().upper() for p in manual_peers.split(',')]

                if not peers:
                    st.warning("No peers found. Try manual peer selection.")
                    return

                # Store peers in session state
                st.session_state.comparison_ticker = ticker
                st.session_state.comparison_peers = peers
                st.session_state.peer_discovery_method = "Auto-detect" if auto_detect else "Manual"

                st.success(f"Found {len(peers)} peers for {ticker}")

            except Exception as e:
                st.error(f"Error finding peers: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
                return

        # Run comparison analysis
        with st.spinner("Comparing metrics..."):
            try:
                comparison_data = asyncio.run(
                    compare_peers(ticker, st.session_state.comparison_peers)
                )

                st.session_state.comparison_data = comparison_data
                st.success("Comparison completed!")

            except Exception as e:
                st.error(f"Error during comparison: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
                return

    # Display results
    if hasattr(st.session_state, 'comparison_data') and st.session_state.comparison_data:
        ticker = st.session_state.comparison_ticker
        peers = st.session_state.comparison_peers
        comparison = st.session_state.comparison_data

        st.markdown("---")
        st.markdown(f"## Comparison Results: {ticker}")
        st.markdown(f"**Peers:** {', '.join(peers)}")
        st.markdown(f"**Discovery Method:** {st.session_state.peer_discovery_method}")

        # Peer overview cards
        st.markdown("### Peer Companies")

        # Display peer cards in columns
        cols = st.columns(min(len(peers) + 1, 4))

        # Target company
        with cols[0]:
            st.markdown(f"""
            <div class="peer-card" style="border: 2px solid #667eea;">
                <h4>{ticker}</h4>
                <p><strong>Target Company</strong></p>
            </div>
            """, unsafe_allow_html=True)

        # Peer companies
        for i, peer in enumerate(peers[:3]):
            with cols[i + 1]:
                st.markdown(f"""
                <div class="peer-card">
                    <h4>{peer}</h4>
                    <p>Peer Company</p>
                </div>
                """, unsafe_allow_html=True)

        if len(peers) > 3:
            st.info(f"+ {len(peers) - 3} more peers")

        st.markdown("---")

        # Comparison tables
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Valuation",
            "📈 Growth",
            "💰 Profitability",
            "🏦 Financial Health"
        ])

        with tab1:
            st.markdown("### Valuation Metrics")

            # Sample valuation data (replace with actual comparison data)
            valuation_data = {
                'Company': [ticker] + peers,
                'P/E Ratio': [25.4, 28.1, 22.3, 19.7, 31.2],
                'P/B Ratio': [7.2, 6.8, 5.9, 4.3, 8.1],
                'EV/EBITDA': [18.5, 20.1, 16.3, 14.8, 22.4],
                'Price/Sales': [6.3, 7.1, 5.4, 4.8, 8.2]
            }

            df_valuation = pd.DataFrame(valuation_data)
            st.dataframe(df_valuation, use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("### Growth Metrics")

            growth_data = {
                'Company': [ticker] + peers,
                'Revenue Growth (%)': [12.5, 15.2, 10.8, 8.3, 18.9],
                'EPS Growth (%)': [18.2, 20.5, 14.3, 11.7, 25.1],
                'Asset Growth (%)': [8.7, 10.2, 7.5, 6.1, 12.4]
            }

            df_growth = pd.DataFrame(growth_data)
            st.dataframe(df_growth, use_container_width=True, hide_index=True)

        with tab3:
            st.markdown("### Profitability Metrics")

            profit_data = {
                'Company': [ticker] + peers,
                'Net Margin (%)': [25.3, 28.1, 22.7, 19.4, 31.5],
                'ROE (%)': [48.2, 52.3, 43.1, 38.7, 56.8],
                'ROA (%)': [18.5, 20.1, 16.8, 14.2, 22.7],
                'ROIC (%)': [32.1, 35.4, 28.9, 24.5, 38.2]
            }

            df_profit = pd.DataFrame(profit_data)
            st.dataframe(df_profit, use_container_width=True, hide_index=True)

        with tab4:
            st.markdown("### Financial Health Metrics")

            health_data = {
                'Company': [ticker] + peers,
                'Current Ratio': [1.8, 2.1, 1.6, 1.4, 2.3],
                'Debt/Equity': [0.45, 0.38, 0.52, 0.61, 0.33],
                'Interest Coverage': [28.5, 32.1, 24.3, 19.8, 35.7]
            }

            df_health = pd.DataFrame(health_data)
            st.dataframe(df_health, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Rankings and visualizations
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Overall Rankings")

            # Sample ranking data
            ranking_data = pd.DataFrame({
                'ticker': [ticker] + peers,
                'score': [85, 78, 82, 71, 88]
            }).sort_values('score', ascending=False)

            for idx, row in ranking_data.iterrows():
                rank = idx + 1
                rank_class = f"rank-{rank}" if rank <= 3 else "rank-other"

                st.markdown(f"""
                <div class="peer-card">
                    <span class="rank-badge {rank_class}">#{rank}</span>
                    <strong style="margin-left: 1rem;">{row['ticker']}</strong>
                    <span style="float: right; color: #667eea; font-weight: bold;">Score: {row['score']}</span>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("### Performance Comparison")
            render_ranking_chart(ranking_data)

        st.markdown("---")

        # Radar chart comparison
        st.markdown("### Multi-Dimensional Analysis")

        # Sample radar chart data
        radar_data = {
            'Valuation': 75,
            'Growth': 85,
            'Profitability': 90,
            'Financial Health': 80,
            'Market Position': 88
        }

        render_comparison_radar_chart(radar_data, ticker)

        # Export options
        st.markdown("---")
        st.markdown("### Export Comparison")

        col1, col2 = st.columns(2)

        with col1:
            # Combine all comparison data
            all_data = pd.concat([
                df_valuation.set_index('Company'),
                df_growth.set_index('Company'),
                df_profit.set_index('Company'),
                df_health.set_index('Company')
            ], axis=1)

            csv_data = all_data.to_csv()

            st.download_button(
                label="📥 Export Comparison CSV",
                data=csv_data,
                file_name=f"peer_comparison_{ticker}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            # Export ranking data
            ranking_csv = ranking_data.to_csv(index=False)

            st.download_button(
                label="📥 Export Rankings CSV",
                data=ranking_csv,
                file_name=f"peer_rankings_{ticker}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

    else:
        # Show example comparisons
        st.markdown("### Example Comparisons")

        examples = [
            ("AAPL", "Technology - Consumer Electronics"),
            ("JPM", "Financial Services - Banking"),
            ("PFE", "Healthcare - Pharmaceuticals")
        ]

        for ticker_ex, sector in examples:
            with st.expander(f"{ticker_ex} - {sector}"):
                st.markdown(f"""
                Compare **{ticker_ex}** with industry peers in the {sector} sector.

                This analysis will include:
                - Valuation metrics comparison
                - Growth trends analysis
                - Profitability assessment
                - Financial health evaluation
                """)

                if st.button(f"Compare {ticker_ex}", key=f"btn_{ticker_ex}"):
                    st.session_state.example_ticker = ticker_ex
                    st.rerun()


if __name__ == "__main__":
    main()
