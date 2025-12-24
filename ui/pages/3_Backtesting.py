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


# Built-in trading strategies
def buy_and_hold_strategy(data, date):
    """Buy and hold strategy - always hold."""
    return "BUY"


def sma_crossover_strategy(data, date, short_window=20, long_window=50):
    """Simple Moving Average crossover strategy."""
    if len(data.loc[:date]) < long_window:
        return "HOLD"

    short_ma = data.loc[:date, 'Close'].rolling(window=short_window).mean().iloc[-1]
    long_ma = data.loc[:date, 'Close'].rolling(window=long_window).mean().iloc[-1]

    if short_ma > long_ma:
        return "BUY"
    elif short_ma < long_ma:
        return "SELL"
    return "HOLD"


def rsi_strategy(data, date, period=14, oversold=30, overbought=70):
    """RSI-based mean reversion strategy."""
    if len(data.loc[:date]) < period + 1:
        return "HOLD"

    prices = data.loc[:date, 'Close']
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 0
    rsi = 100 - (100 / (1 + rs))

    if rsi < oversold:
        return "BUY"
    elif rsi > overbought:
        return "SELL"
    return "HOLD"


def momentum_strategy(data, date, lookback=20):
    """Momentum strategy - buy on positive momentum."""
    if len(data.loc[:date]) < lookback:
        return "HOLD"

    prices = data.loc[:date, 'Close']
    momentum = (prices.iloc[-1] - prices.iloc[-lookback]) / prices.iloc[-lookback]

    if momentum > 0.02:  # 2% positive momentum
        return "BUY"
    elif momentum < -0.02:  # 2% negative momentum
        return "SELL"
    return "HOLD"


STRATEGIES = {
    "Buy and Hold": buy_and_hold_strategy,
    "SMA Crossover (20/50)": lambda data, date: sma_crossover_strategy(data, date, 20, 50),
    "SMA Crossover (10/30)": lambda data, date: sma_crossover_strategy(data, date, 10, 30),
    "RSI Mean Reversion": rsi_strategy,
    "Momentum": momentum_strategy,
}

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

    if hasattr(result, 'trades') and result.trades is not None and not result.trades.empty:
        # result.trades is already a DataFrame from get_trade_log()
        df = result.trades.copy()

        # Format columns for display if they exist
        if 'price' in df.columns:
            df['price'] = df['price'].apply(lambda x: format_currency(x) if pd.notna(x) else '')
        if 'value' in df.columns:
            df['value'] = df['value'].apply(lambda x: format_currency(x) if pd.notna(x) else '')
        if 'pnl' in df.columns:
            df['pnl'] = df['pnl'].apply(lambda x: format_currency(x) if pd.notna(x) else '')

        # Rename columns for better display
        column_renames = {
            'date': 'Date',
            'ticker': 'Ticker',
            'direction': 'Type',
            'shares': 'Shares',
            'price': 'Price',
            'value': 'Value',
            'pnl': 'P&L',
            'commission': 'Commission'
        }
        df = df.rename(columns={k: v for k, v in column_renames.items() if k in df.columns})

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

        # Strategy selection
        st.markdown("### Strategy Selection")

        strategy_name = st.selectbox(
            "Trading Strategy",
            options=list(STRATEGIES.keys()),
            help="Select a trading strategy to backtest"
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
                    commission_rate=commission
                )

                engine = BacktestEngine(
                    config=config,
                    data_loader=data_loader
                )

                # Get selected strategy function
                strategy_func = STRATEGIES[strategy_name]

                # Run backtest
                result = engine.run_backtest(
                    ticker=ticker,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    strategy_func=strategy_func
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

        if hasattr(result, 'equity_curve') and result.equity_curve is not None and not result.equity_curve.empty:
            # Convert Series to DataFrame with required columns
            equity_df = pd.DataFrame({
                'date': result.equity_curve.index,
                'equity': result.equity_curve.values
            })
            render_equity_curve(
                equity_df,
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
            if hasattr(result, 'trades') and result.trades is not None and not result.trades.empty:
                # Export trades to CSV - result.trades is already a DataFrame
                csv_data = result.trades.to_csv(index=False)

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
