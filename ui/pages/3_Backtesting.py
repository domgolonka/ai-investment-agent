"""
Backtesting Page
Test investment strategies against historical data.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backtesting import (
    BacktestEngine,
    BacktestConfig,
    HistoricalDataLoader,
    BacktestReport
)
from ui.components.chart_view import render_equity_curve
from ui.utils import format_currency, format_percentage, validate_ticker

st.set_page_config(
    page_title="Backtesting - AI Investment Agent",
    page_icon="🔬",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .backtest-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-box {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        color: #666;
        font-size: 0.9rem;
    }
    .positive-metric {
        color: #28a745;
    }
    .negative-metric {
        color: #dc3545;
    }
    </style>
    """, unsafe_allow_html=True)


def display_performance_metrics(result):
    """Display backtest performance metrics."""
    st.markdown("### Performance Metrics")

    metrics = result.metrics if hasattr(result, 'metrics') else {}

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_return = metrics.get('total_return', 0) * 100
        return_class = "positive-metric" if total_return > 0 else "negative-metric"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Total Return</div>
            <div class="metric-value {return_class}">{total_return:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        sharpe = metrics.get('sharpe_ratio', 0)
        sharpe_class = "positive-metric" if sharpe > 0 else "negative-metric"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value {sharpe_class}">{sharpe:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        max_dd = metrics.get('max_drawdown', 0) * 100
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value negative-metric">{max_dd:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        win_rate = metrics.get('win_rate', 0) * 100
        win_class = "positive-metric" if win_rate > 50 else "negative-metric"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value {win_class}">{win_rate:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # Additional metrics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Trades", metrics.get('total_trades', 0))

    with col2:
        st.metric("Winning Trades", metrics.get('winning_trades', 0))

    with col3:
        st.metric("Losing Trades", metrics.get('losing_trades', 0))

    with col4:
        sortino = metrics.get('sortino_ratio', 0)
        st.metric("Sortino Ratio", f"{sortino:.2f}")


def display_trade_history(result):
    """Display trade history table."""
    st.markdown("### Trade History")

    if hasattr(result, 'trades') and result.trades:
        trades_data = []

        for trade in result.trades:
            trades_data.append({
                'Date': trade.date if hasattr(trade, 'date') else '',
                'Type': trade.type if hasattr(trade, 'type') else '',
                'Price': format_currency(trade.price) if hasattr(trade, 'price') else '',
                'Quantity': trade.quantity if hasattr(trade, 'quantity') else '',
                'Value': format_currency(trade.value) if hasattr(trade, 'value') else '',
                'P&L': format_currency(trade.pnl) if hasattr(trade, 'pnl') else ''
            })

        df = pd.DataFrame(trades_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No trades executed during backtest period")


def main():
    """Main backtesting page."""

    st.markdown('<div class="backtest-header">', unsafe_allow_html=True)
    st.markdown("# 🔬 Backtesting Engine")
    st.markdown("Test your investment strategies against historical data")
    st.markdown('</div>', unsafe_allow_html=True)

    # Sidebar - Configuration
    with st.sidebar:
        st.markdown("## Backtest Configuration")

        # Ticker input
        ticker = st.text_input(
            "Ticker Symbol",
            value="AAPL",
            help="Enter stock ticker to backtest"
        ).upper()

        # Date range
        st.markdown("### Date Range")

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=365),
                max_value=datetime.now()
            )

        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now(),
                max_value=datetime.now()
            )

        # Strategy parameters
        st.markdown("### Strategy Parameters")

        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=1000,
            max_value=10000000,
            value=100000,
            step=10000
        )

        position_size = st.slider(
            "Position Size (%)",
            min_value=1,
            max_value=100,
            value=10,
            help="Percentage of capital to use per trade"
        ) / 100

        commission = st.number_input(
            "Commission per Trade ($)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.1
        )

        # Run backtest button
        st.markdown("---")
        run_backtest_btn = st.button(
            "🚀 Run Backtest",
            type="primary",
            use_container_width=True,
            disabled=not ticker
        )

    # Main content
    if not ticker:
        st.info("👈 Enter a ticker symbol in the sidebar to begin backtesting")
        return

    # Validate ticker
    validation = validate_ticker(ticker)
    if not validation["valid"]:
        st.error(f"Invalid ticker: {validation['message']}")
        return

    # Validate date range
    if start_date >= end_date:
        st.error("Start date must be before end date")
        return

    # Run backtest
    if run_backtest_btn:
        with st.spinner(f"Running backtest for {ticker}..."):
            try:
                # Initialize backtest engine
                data_loader = HistoricalDataLoader()

                config = BacktestConfig(
                    initial_capital=initial_capital,
                    position_size=position_size,
                    commission=commission
                )

                engine = BacktestEngine(
                    initial_capital=initial_capital,
                    position_size=position_size,
                    data_loader=data_loader
                )

                # Run backtest
                result = engine.run_backtest(
                    ticker=ticker,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d")
                )

                # Store result in session state
                st.session_state.backtest_result = result
                st.session_state.backtest_ticker = ticker
                st.session_state.backtest_start = start_date
                st.session_state.backtest_end = end_date

                st.success("Backtest completed successfully!")

            except Exception as e:
                st.error(f"Backtest failed: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
                return

    # Display results
    if hasattr(st.session_state, 'backtest_result') and st.session_state.backtest_result:
        result = st.session_state.backtest_result

        st.markdown("---")
        st.markdown(f"## Results: {st.session_state.backtest_ticker}")
        st.markdown(f"**Period:** {st.session_state.backtest_start} to {st.session_state.backtest_end}")

        # Performance metrics
        display_performance_metrics(result)

        st.markdown("---")

        # Equity curve
        st.markdown("### Equity Curve")

        if hasattr(result, 'equity_curve') and result.equity_curve:
            render_equity_curve(
                result.equity_curve,
                ticker=st.session_state.backtest_ticker
            )
        else:
            st.warning("No equity curve data available")

        st.markdown("---")

        # Trade history
        display_trade_history(result)

        st.markdown("---")

        # Additional analysis
        with st.expander("📊 Detailed Statistics"):
            if hasattr(result, 'metrics'):
                metrics = result.metrics

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### Returns Analysis")
                    st.metric("Annualized Return", format_percentage(metrics.get('annualized_return', 0)))
                    st.metric("Volatility", format_percentage(metrics.get('volatility', 0)))
                    st.metric("Average Win", format_currency(metrics.get('avg_win', 0)))
                    st.metric("Average Loss", format_currency(metrics.get('avg_loss', 0)))

                with col2:
                    st.markdown("#### Risk Metrics")
                    st.metric("Max Consecutive Losses", metrics.get('max_consecutive_losses', 0))
                    st.metric("Calmar Ratio", f"{metrics.get('calmar_ratio', 0):.2f}")
                    st.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
                    st.metric("Recovery Factor", f"{metrics.get('recovery_factor', 0):.2f}")

        # Export results
        st.markdown("---")
        st.markdown("### Export Results")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📄 Generate Report", use_container_width=True):
                try:
                    report = BacktestReport(result)
                    report_text = report.generate_text_report()

                    st.download_button(
                        label="📥 Download Report",
                        data=report_text,
                        file_name=f"backtest_{st.session_state.backtest_ticker}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")

        with col2:
            if hasattr(result, 'trades') and result.trades:
                # Export trades to CSV
                trades_data = []
                for trade in result.trades:
                    trades_data.append({
                        'date': trade.date if hasattr(trade, 'date') else '',
                        'type': trade.type if hasattr(trade, 'type') else '',
                        'price': trade.price if hasattr(trade, 'price') else 0,
                        'quantity': trade.quantity if hasattr(trade, 'quantity') else 0,
                        'value': trade.value if hasattr(trade, 'value') else 0,
                        'pnl': trade.pnl if hasattr(trade, 'pnl') else 0
                    })

                df = pd.DataFrame(trades_data)
                csv_data = df.to_csv(index=False)

                st.download_button(
                    label="📥 Export Trades CSV",
                    data=csv_data,
                    file_name=f"trades_{st.session_state.backtest_ticker}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    else:
        # Show example backtests
        st.markdown("### Example Backtests")

        col1, col2, col3 = st.columns(3)

        examples = [
            ("AAPL", "Apple Inc."),
            ("MSFT", "Microsoft"),
            ("NVDA", "NVIDIA")
        ]

        for col, (ticker_ex, name) in zip([col1, col2, col3], examples):
            with col:
                st.markdown(f"**{name}**")
                st.markdown(f"Ticker: {ticker_ex}")
                if st.button(f"Backtest {ticker_ex}", use_container_width=True):
                    st.session_state.example_ticker = ticker_ex
                    st.rerun()


if __name__ == "__main__":
    main()
