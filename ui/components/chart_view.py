"""
Chart View Component
Renders interactive charts using Plotly for price, volume, and equity curves.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, List


def render_price_chart(
    ticker: str,
    period: str = "1y",
    show_volume: bool = True,
    indicators: Optional[List[str]] = None
) -> None:
    """
    Render interactive price chart with volume.

    Args:
        ticker: Stock ticker symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
        show_volume: Whether to show volume subplot
        indicators: List of technical indicators to add
    """
    try:
        # Fetch data
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)

        if df.empty:
            st.error(f"No data available for {ticker}")
            return

        # Create figure with secondary y-axis for volume
        if show_volume:
            fig = go.Figure()

            # Candlestick chart
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name='Price',
                    increasing_line_color='#26a69a',
                    decreasing_line_color='#ef5350'
                )
            )

            # Volume bars
            colors = ['#26a69a' if close >= open else '#ef5350'
                     for close, open in zip(df['Close'], df['Open'])]

            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['Volume'],
                    name='Volume',
                    marker_color=colors,
                    yaxis='y2',
                    opacity=0.5
                )
            )

            # Layout with secondary y-axis
            fig.update_layout(
                title=f"{ticker} Price and Volume",
                yaxis=dict(title='Price ($)', side='left'),
                yaxis2=dict(
                    title='Volume',
                    overlaying='y',
                    side='right',
                    showgrid=False
                ),
                xaxis=dict(title='Date', rangeslider=dict(visible=False)),
                hovermode='x unified',
                height=600
            )

        else:
            # Simple line chart
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color='#667eea', width=2)
                )
            )

            fig.update_layout(
                title=f"{ticker} Price Chart",
                xaxis_title='Date',
                yaxis_title='Price ($)',
                hovermode='x unified',
                height=500
            )

        # Add technical indicators if requested
        if indicators:
            for indicator in indicators:
                if indicator == 'MA20':
                    ma20 = df['Close'].rolling(window=20).mean()
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=ma20,
                            mode='lines',
                            name='MA(20)',
                            line=dict(color='orange', width=1, dash='dash')
                        )
                    )
                elif indicator == 'MA50':
                    ma50 = df['Close'].rolling(window=50).mean()
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=ma50,
                            mode='lines',
                            name='MA(50)',
                            line=dict(color='red', width=1, dash='dash')
                        )
                    )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error rendering chart: {str(e)}")


def render_equity_curve(
    equity_data: List[Dict],
    ticker: Optional[str] = None,
    show_drawdown: bool = True
) -> None:
    """
    Render equity curve from backtest results.

    Args:
        equity_data: List of equity values over time
        ticker: Optional ticker symbol for title
        show_drawdown: Whether to show drawdown subplot
    """
    try:
        # Convert to DataFrame
        if isinstance(equity_data, list):
            df = pd.DataFrame(equity_data)
        else:
            df = equity_data

        # Ensure we have required columns
        if 'date' not in df.columns or 'equity' not in df.columns:
            st.error("Equity data must contain 'date' and 'equity' columns")
            return

        # Create figure
        fig = go.Figure()

        # Equity curve
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['equity'],
                mode='lines',
                name='Equity',
                line=dict(color='#667eea', width=2),
                fill='tonexty',
                fillcolor='rgba(102, 126, 234, 0.2)'
            )
        )

        # Add initial capital line if available
        if len(df) > 0:
            initial_capital = df['equity'].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[df['date'].iloc[0], df['date'].iloc[-1]],
                    y=[initial_capital, initial_capital],
                    mode='lines',
                    name='Initial Capital',
                    line=dict(color='gray', width=1, dash='dash')
                )
            )

        # Layout
        title = f"Equity Curve - {ticker}" if ticker else "Equity Curve"
        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title='Portfolio Value ($)',
            hovermode='x unified',
            height=500,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

        # Drawdown chart
        if show_drawdown and len(df) > 0:
            # Calculate drawdown
            rolling_max = df['equity'].expanding().max()
            drawdown = (df['equity'] - rolling_max) / rolling_max * 100

            fig_dd = go.Figure()

            fig_dd.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=drawdown,
                    mode='lines',
                    name='Drawdown',
                    line=dict(color='#dc3545', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(220, 53, 69, 0.2)'
                )
            )

            fig_dd.update_layout(
                title='Drawdown Analysis',
                xaxis_title='Date',
                yaxis_title='Drawdown (%)',
                hovermode='x unified',
                height=300
            )

            st.plotly_chart(fig_dd, use_container_width=True)

    except Exception as e:
        st.error(f"Error rendering equity curve: {str(e)}")


def render_performance_chart(
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    title: str = "Performance Comparison"
) -> None:
    """
    Render cumulative returns chart.

    Args:
        returns: Portfolio returns series
        benchmark_returns: Optional benchmark returns
        title: Chart title
    """
    try:
        # Calculate cumulative returns
        cum_returns = (1 + returns).cumprod() - 1

        fig = go.Figure()

        # Portfolio returns
        fig.add_trace(
            go.Scatter(
                x=returns.index,
                y=cum_returns * 100,
                mode='lines',
                name='Portfolio',
                line=dict(color='#667eea', width=2)
            )
        )

        # Benchmark returns
        if benchmark_returns is not None:
            cum_benchmark = (1 + benchmark_returns).cumprod() - 1
            fig.add_trace(
                go.Scatter(
                    x=benchmark_returns.index,
                    y=cum_benchmark * 100,
                    mode='lines',
                    name='Benchmark',
                    line=dict(color='gray', width=2, dash='dash')
                )
            )

        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title='Cumulative Return (%)',
            hovermode='x unified',
            height=500,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error rendering performance chart: {str(e)}")


def render_correlation_heatmap(
    correlation_matrix: pd.DataFrame,
    title: str = "Correlation Matrix"
) -> None:
    """
    Render correlation heatmap.

    Args:
        correlation_matrix: Correlation matrix DataFrame
        title: Chart title
    """
    try:
        fig = go.Figure(
            data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.index,
                colorscale='RdYlGn',
                zmid=0,
                text=correlation_matrix.values,
                texttemplate='%{text:.2f}',
                textfont={"size": 10},
                colorbar=dict(title="Correlation")
            )
        )

        fig.update_layout(
            title=title,
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error rendering correlation heatmap: {str(e)}")


def render_pie_chart(
    data: Dict[str, float],
    title: str = "Distribution",
    colors: Optional[List[str]] = None
) -> None:
    """
    Render pie chart.

    Args:
        data: Dictionary of labels and values
        title: Chart title
        colors: Optional list of colors
    """
    try:
        labels = list(data.keys())
        values = list(data.values())

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=colors) if colors else None,
                    textposition='inside',
                    textinfo='label+percent'
                )
            ]
        )

        fig.update_layout(
            title=title,
            height=400,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error rendering pie chart: {str(e)}")
