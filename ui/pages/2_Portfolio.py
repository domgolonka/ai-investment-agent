"""
Portfolio Management Page
Upload, manage, and analyze investment portfolios.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.portfolio import (
    PortfolioManager,
    PnLCalculator,
    PortfolioStorage,
    Position
)
from src.main import run_analysis
from ui.utils import format_currency, format_percentage, format_timestamp

st.set_page_config(
    page_title="Portfolio - AI Investment Agent",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .portfolio-header {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .positive {
        color: #28a745;
        font-weight: bold;
    }
    .negative {
        color: #dc3545;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)


def load_portfolio_from_csv(file) -> pd.DataFrame:
    """Load portfolio from uploaded CSV file."""
    try:
        df = pd.read_csv(file)
        required_columns = ['ticker', 'quantity', 'cost_basis']

        if not all(col in df.columns for col in required_columns):
            st.error(f"CSV must contain columns: {', '.join(required_columns)}")
            return None

        return df

    except Exception as e:
        st.error(f"Error loading CSV: {str(e)}")
        return None


def load_portfolio_from_excel(file) -> pd.DataFrame:
    """Load portfolio from uploaded Excel file."""
    try:
        df = pd.read_excel(file)
        required_columns = ['ticker', 'quantity', 'cost_basis']

        if not all(col in df.columns for col in required_columns):
            st.error(f"Excel must contain columns: {', '.join(required_columns)}")
            return None

        return df

    except Exception as e:
        st.error(f"Error loading Excel: {str(e)}")
        return None


def create_portfolio_from_dataframe(df: pd.DataFrame, name: str) -> PortfolioManager:
    """Create PortfolioManager from DataFrame."""
    manager = PortfolioManager(name=name)

    for _, row in df.iterrows():
        position = Position(
            ticker=row['ticker'],
            quantity=float(row['quantity']),
            cost_basis=float(row['cost_basis']),
            currency=row.get('currency', 'USD'),
            purchase_date=pd.to_datetime(row.get('purchase_date', datetime.now()))
        )
        manager.add_position(position)

    return manager


def display_portfolio_summary(manager: PortfolioManager, calculator: PnLCalculator):
    """Display portfolio summary metrics."""
    metrics = calculator.calculate_portfolio_metrics()

    st.markdown("### Portfolio Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Value", format_currency(metrics.get("total_value", 0)))
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        total_pnl = metrics.get("total_pnl", 0)
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "Total P&L",
            format_currency(total_pnl),
            delta=format_percentage(metrics.get("total_return_pct", 0))
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Cost", format_currency(metrics.get("total_cost", 0)))
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Positions", len(manager.positions))
        st.markdown('</div>', unsafe_allow_html=True)


def display_positions_table(manager: PortfolioManager, calculator: PnLCalculator):
    """Display detailed positions table."""
    st.markdown("### Positions")

    positions_data = []

    for ticker, position in manager.positions.items():
        pnl = calculator.calculate_position_pnl(ticker)

        positions_data.append({
            'Ticker': ticker,
            'Quantity': position.quantity,
            'Cost Basis': format_currency(position.cost_basis),
            'Current Price': format_currency(pnl.get("current_price", 0)),
            'Market Value': format_currency(pnl.get("market_value", 0)),
            'P&L': format_currency(pnl.get("total_pnl", 0)),
            'Return %': format_percentage(pnl.get("return_pct", 0)),
            'Currency': position.currency
        })

    if positions_data:
        df = pd.DataFrame(positions_data)

        # Style the dataframe
        def color_pnl(val):
            if 'P&L' in str(val) or 'Return' in str(val):
                if '-' in str(val):
                    return 'color: #dc3545'
                elif val != '-' and val != '$0.00' and val != '0.00%':
                    return 'color: #28a745'
            return ''

        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No positions in portfolio")


def main():
    """Main portfolio management page."""

    st.markdown('<div class="portfolio-header">', unsafe_allow_html=True)
    st.markdown("# 📈 Portfolio Management")
    st.markdown("Upload, analyze, and manage your investment portfolios")
    st.markdown('</div>', unsafe_allow_html=True)

    # Initialize session state
    if 'portfolio_manager' not in st.session_state:
        st.session_state.portfolio_manager = None
    if 'portfolio_calculator' not in st.session_state:
        st.session_state.portfolio_calculator = None

    # Sidebar - Upload and controls
    with st.sidebar:
        st.markdown("## Portfolio Upload")

        # Portfolio name
        portfolio_name = st.text_input(
            "Portfolio Name",
            value="My Portfolio",
            help="Give your portfolio a name"
        )

        # File upload
        st.markdown("### Upload Portfolio")
        upload_format = st.radio(
            "Format",
            ["CSV", "Excel"],
            horizontal=True
        )

        if upload_format == "CSV":
            uploaded_file = st.file_uploader(
                "Upload CSV file",
                type=['csv'],
                help="CSV must contain: ticker, quantity, cost_basis"
            )
        else:
            uploaded_file = st.file_uploader(
                "Upload Excel file",
                type=['xlsx', 'xls'],
                help="Excel must contain: ticker, quantity, cost_basis"
            )

        # Sample template download
        st.markdown("### Download Template")
        template_data = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'quantity': [100, 50, 25],
            'cost_basis': [150.00, 300.00, 2800.00],
            'currency': ['USD', 'USD', 'USD'],
            'purchase_date': ['2024-01-15', '2024-02-20', '2024-03-10']
        })

        csv_template = template_data.to_csv(index=False)
        st.download_button(
            label="📄 Download CSV Template",
            data=csv_template,
            file_name="portfolio_template.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Process uploaded file
        if uploaded_file:
            if st.button("📂 Load Portfolio", type="primary", use_container_width=True):
                with st.spinner("Loading portfolio..."):
                    if upload_format == "CSV":
                        df = load_portfolio_from_csv(uploaded_file)
                    else:
                        df = load_portfolio_from_excel(uploaded_file)

                    if df is not None:
                        manager = create_portfolio_from_dataframe(df, portfolio_name)
                        calculator = PnLCalculator(manager)

                        st.session_state.portfolio_manager = manager
                        st.session_state.portfolio_calculator = calculator

                        st.success(f"Loaded {len(manager.positions)} positions")

        st.markdown("---")

        # Analysis options
        if st.session_state.portfolio_manager:
            st.markdown("## Analysis Options")

            if st.button("🔄 Refresh Prices", use_container_width=True):
                st.rerun()

            if st.button("💾 Save Portfolio", use_container_width=True):
                storage = PortfolioStorage("portfolio.db")
                storage.save_portfolio(st.session_state.portfolio_manager)
                st.success("Portfolio saved!")

    # Main content
    if not st.session_state.portfolio_manager:
        st.info("👈 Upload a portfolio file to get started")

        st.markdown("### Getting Started")
        st.markdown("""
        1. Download the CSV template from the sidebar
        2. Fill in your positions (ticker, quantity, cost_basis)
        3. Upload the completed file
        4. View your portfolio analysis
        """)

        st.markdown("### Required Columns")
        st.markdown("""
        - **ticker**: Stock symbol (e.g., AAPL, MSFT)
        - **quantity**: Number of shares
        - **cost_basis**: Average purchase price per share
        - **currency** (optional): Currency code (default: USD)
        - **purchase_date** (optional): Purchase date (default: today)
        """)

        return

    # Display portfolio
    manager = st.session_state.portfolio_manager
    calculator = st.session_state.portfolio_calculator

    # Summary metrics
    display_portfolio_summary(manager, calculator)

    st.markdown("---")

    # Positions table
    display_positions_table(manager, calculator)

    st.markdown("---")

    # Portfolio analysis section
    st.markdown("### Portfolio Analysis")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        Run AI-powered analysis on your entire portfolio or individual positions.
        This will analyze each holding and provide comprehensive insights.
        """)

    with col2:
        analysis_mode = st.selectbox(
            "Analysis Mode",
            ["Quick", "Deep"],
            help="Select analysis depth"
        )

    # Individual position analysis
    st.markdown("#### Analyze Individual Position")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        selected_ticker = st.selectbox(
            "Select Position",
            options=list(manager.positions.keys()),
            help="Choose a position to analyze"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Analyze Position", use_container_width=True):
            st.session_state.analyze_ticker = selected_ticker
            st.session_state.analyze_mode = analysis_mode

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📊 Analyze All", use_container_width=True):
            st.session_state.analyze_all = True
            st.session_state.analyze_mode = analysis_mode

    # Run individual analysis
    if hasattr(st.session_state, 'analyze_ticker'):
        ticker = st.session_state.analyze_ticker
        quick_mode = st.session_state.analyze_mode == "Quick"

        with st.spinner(f"Analyzing {ticker}..."):
            try:
                async def run_async():
                    return await run_analysis(ticker, quick_mode)

                result = asyncio.run(run_async())

                if result:
                    st.success(f"Analysis complete for {ticker}")

                    with st.expander(f"📋 Analysis Results: {ticker}", expanded=True):
                        if result.get("final_trade_decision"):
                            st.markdown("**Decision:**")
                            st.info(result["final_trade_decision"])

                        if result.get("investment_plan"):
                            st.markdown("**Investment Plan:**")
                            st.write(result["investment_plan"])

                del st.session_state.analyze_ticker

            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
                del st.session_state.analyze_ticker

    # Export options
    st.markdown("---")
    st.markdown("### Export Portfolio")

    col1, col2 = st.columns(2)

    with col1:
        # Export to CSV
        export_data = []
        for ticker, position in manager.positions.items():
            export_data.append({
                'ticker': ticker,
                'quantity': position.quantity,
                'cost_basis': position.cost_basis,
                'currency': position.currency,
                'purchase_date': position.purchase_date
            })

        export_df = pd.DataFrame(export_data)
        csv_data = export_df.to_csv(index=False)

        st.download_button(
            label="📥 Export CSV",
            data=csv_data,
            file_name=f"{portfolio_name}_{format_timestamp()}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        # Export with current prices
        export_data_full = []
        for ticker, position in manager.positions.items():
            pnl = calculator.calculate_position_pnl(ticker)
            export_data_full.append({
                'ticker': ticker,
                'quantity': position.quantity,
                'cost_basis': position.cost_basis,
                'current_price': pnl.get("current_price", 0),
                'market_value': pnl.get("market_value", 0),
                'pnl': pnl.get("total_pnl", 0),
                'return_pct': pnl.get("return_pct", 0),
                'currency': position.currency
            })

        export_df_full = pd.DataFrame(export_data_full)
        csv_data_full = export_df_full.to_csv(index=False)

        st.download_button(
            label="📥 Export with Prices",
            data=csv_data_full,
            file_name=f"{portfolio_name}_with_prices_{format_timestamp()}.csv",
            mime="text/csv",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
