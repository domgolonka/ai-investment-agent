"""
Backtesting report generation.

This module provides functionality to generate comprehensive reports
from backtest results, including visualizations and export capabilities.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.backtesting.engine import BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class BacktestReport:
    """
    Generate comprehensive reports from backtest results.

    This class provides methods to:
    - Generate text summaries
    - Export results to various formats (JSON, CSV)
    - Create data for equity curve plotting
    - Generate trade logs
    - Create comparison reports for multiple backtests

    Example:
        >>> report = BacktestReport(result)
        >>> summary = report.generate_summary()
        >>> report.export_results("backtest_results", format="json")
        >>> equity_data = report.generate_equity_curve()
    """

    result: BacktestResult

    def generate_summary(self, detailed: bool = True) -> str:
        """
        Generate a text summary of backtest results.

        Args:
            detailed: If True, include detailed trade statistics

        Returns:
            Formatted text summary
        """
        summary = self.result.summary()

        if detailed:
            # Add additional details
            additional = self._generate_detailed_section()
            summary = f"{summary}\n\n{additional}"

        return summary

    def _generate_detailed_section(self) -> str:
        """Generate detailed statistics section."""
        trades = self.result.trades

        if trades.empty:
            return "No trades executed during backtest period."

        # Calculate additional statistics
        buy_trades = trades[trades["direction"] == "BUY"]
        sell_trades = trades[trades["direction"] == "SELL"]

        lines = [
            "DETAILED TRADE ANALYSIS",
            "-" * 60,
            f"Buy Orders:         {len(buy_trades):>10}",
            f"Sell Orders:        {len(sell_trades):>10}",
        ]

        if len(buy_trades) > 0:
            avg_buy_price = buy_trades["price"].mean()
            lines.append(f"Avg Buy Price:      ${avg_buy_price:>10,.2f}")

        if len(sell_trades) > 0:
            avg_sell_price = sell_trades["price"].mean()
            lines.append(f"Avg Sell Price:     ${avg_sell_price:>10,.2f}")

        # Position holding analysis
        if len(trades) > 0:
            total_volume = trades["value"].sum()
            lines.extend(
                [
                    f"Total Volume:       ${total_volume:>10,.2f}",
                    f"Avg Trade Size:     ${total_volume / len(trades):>10,.2f}",
                ]
            )

        # Drawdown periods
        equity_curve = self.result.equity_curve
        dd_series = (
            (equity_curve - equity_curve.expanding().max())
            / equity_curve.expanding().max()
            * 100
        )

        # Count days in drawdown
        dd_days = (dd_series < -1).sum()  # Days with >1% drawdown
        lines.extend(
            [
                "",
                "DRAWDOWN ANALYSIS",
                "-" * 60,
                f"Days in Drawdown:   {dd_days:>10} ({dd_days / len(equity_curve) * 100:.1f}%)",
                f"Avg Drawdown:       {dd_series[dd_series < 0].mean():>10.2f}%",
            ]
        )

        return "\n".join(lines)

    def generate_equity_curve(self) -> pd.DataFrame:
        """
        Generate equity curve data for plotting.

        Returns:
            DataFrame with columns: date, portfolio_value, drawdown_pct
        """
        equity = self.result.equity_curve
        running_max = equity.expanding().max()
        drawdown = ((equity - running_max) / running_max) * 100

        df = pd.DataFrame(
            {
                "date": equity.index,
                "portfolio_value": equity.values,
                "drawdown_pct": drawdown.values,
            }
        )

        df.set_index("date", inplace=True)

        return df

    def generate_returns_data(self) -> pd.DataFrame:
        """
        Generate returns data for analysis.

        Returns:
            DataFrame with columns: date, daily_return, cumulative_return
        """
        returns = self.result.returns
        cumulative = (1 + returns).cumprod()

        df = pd.DataFrame(
            {
                "date": returns.index,
                "daily_return": returns.values,
                "cumulative_return": cumulative.values,
            }
        )

        df.set_index("date", inplace=True)

        return df

    def generate_trade_log(self, include_metrics: bool = True) -> pd.DataFrame:
        """
        Generate detailed trade log.

        Args:
            include_metrics: If True, calculate P&L for each trade

        Returns:
            DataFrame with trade details
        """
        trades = self.result.trades.copy()

        if trades.empty:
            return trades

        if include_metrics:
            # Calculate P&L for each trade
            trades["pnl"] = 0.0
            trades["pnl_pct"] = 0.0

            # Track positions to calculate P&L
            positions = {}

            for idx, trade in trades.iterrows():
                ticker = trade["ticker"]
                direction = trade["direction"]
                price = trade["price"]
                shares = trade["shares"]

                if ticker not in positions:
                    positions[ticker] = {"shares": 0, "avg_price": 0, "cost_basis": 0}

                pos = positions[ticker]

                if direction == "BUY":
                    total_cost = pos["cost_basis"] + (shares * price)
                    total_shares = pos["shares"] + shares
                    pos["avg_price"] = (
                        total_cost / total_shares if total_shares > 0 else 0
                    )
                    pos["shares"] = total_shares
                    pos["cost_basis"] = total_cost
                elif direction == "SELL":
                    if pos["shares"] > 0:
                        pnl = (price - pos["avg_price"]) * shares
                        pnl_pct = (
                            (price - pos["avg_price"]) / pos["avg_price"] * 100
                            if pos["avg_price"] > 0
                            else 0
                        )
                        trades.at[idx, "pnl"] = pnl
                        trades.at[idx, "pnl_pct"] = pnl_pct

                        pos["shares"] -= shares
                        pos["cost_basis"] -= shares * pos["avg_price"]

        return trades

    def generate_monthly_returns(self) -> pd.DataFrame:
        """
        Generate monthly returns table.

        Returns:
            DataFrame with monthly returns
        """
        returns = self.result.returns

        # Resample to monthly
        monthly = (1 + returns).resample("M").prod() - 1

        # Create year/month columns
        df = pd.DataFrame(
            {
                "year": monthly.index.year,
                "month": monthly.index.month,
                "return": monthly.values * 100,
            }
        )

        # Pivot to create calendar table
        pivot = df.pivot(index="year", columns="month", values="return")

        # Rename columns to month names
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        pivot.columns = [month_names[i - 1] for i in pivot.columns]

        return pivot

    def generate_benchmark_comparison(self) -> Optional[pd.DataFrame]:
        """
        Generate benchmark comparison data.

        Returns:
            DataFrame comparing strategy vs benchmark, or None if no benchmark
        """
        if self.result.benchmark_returns is None:
            return None

        # Calculate cumulative returns
        strategy_cumulative = (1 + self.result.returns).cumprod()
        benchmark_cumulative = (1 + self.result.benchmark_returns).cumprod()

        # Align dates
        common_dates = strategy_cumulative.index.intersection(
            benchmark_cumulative.index
        )

        df = pd.DataFrame(
            {
                "date": common_dates,
                "strategy": strategy_cumulative.loc[common_dates].values,
                "benchmark": benchmark_cumulative.loc[common_dates].values,
            }
        )

        df.set_index("date", inplace=True)

        # Calculate excess returns
        df["excess"] = df["strategy"] - df["benchmark"]

        return df

    def export_results(
        self,
        output_path: str,
        format: str = "json",
        include_trades: bool = True,
    ) -> Path:
        """
        Export backtest results to file.

        Args:
            output_path: Base output path (without extension)
            format: Export format ('json', 'csv', or 'excel')
            include_trades: Whether to include trade log

        Returns:
            Path to exported file

        Raises:
            ValueError: If format is not supported
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            return self._export_json(output_path, include_trades)
        elif format == "csv":
            return self._export_csv(output_path, include_trades)
        elif format == "excel":
            return self._export_excel(output_path, include_trades)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_json(self, output_path: Path, include_trades: bool) -> Path:
        """Export results to JSON."""
        output_file = output_path.with_suffix(".json")

        # Prepare data
        data = {
            "metadata": {
                "ticker": self.result.ticker,
                "start_date": self.result.start_date.isoformat(),
                "end_date": self.result.end_date.isoformat(),
                "initial_capital": self.result.config.initial_capital,
                "position_size": self.result.config.position_size,
                "commission_rate": self.result.config.commission_rate,
            },
            "metrics": self._serialize_metrics(self.result.metrics),
            "equity_curve": self.result.equity_curve.to_dict(),
        }

        if include_trades and not self.result.trades.empty:
            data["trades"] = self.result.trades.to_dict(orient="records")

        # Write to file
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Exported results to {output_file}")
        return output_file

    def _export_csv(self, output_path: Path, include_trades: bool) -> Path:
        """Export results to CSV."""
        output_dir = output_path.parent / output_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export equity curve
        equity_file = output_dir / "equity_curve.csv"
        equity_df = self.generate_equity_curve()
        equity_df.to_csv(equity_file)

        # Export metrics
        metrics_file = output_dir / "metrics.csv"
        metrics_df = pd.DataFrame([self._serialize_metrics(self.result.metrics)])
        metrics_df.to_csv(metrics_file, index=False)

        # Export trades
        if include_trades and not self.result.trades.empty:
            trades_file = output_dir / "trades.csv"
            self.result.trades.to_csv(trades_file)

        # Export returns
        returns_file = output_dir / "returns.csv"
        returns_df = self.generate_returns_data()
        returns_df.to_csv(returns_file)

        logger.info(f"Exported results to {output_dir}")
        return output_dir

    def _export_excel(self, output_path: Path, include_trades: bool) -> Path:
        """Export results to Excel with multiple sheets."""
        output_file = output_path.with_suffix(".xlsx")

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            # Summary sheet
            summary_df = pd.DataFrame([self._serialize_metrics(self.result.metrics)])
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

            # Equity curve sheet
            equity_df = self.generate_equity_curve()
            equity_df.to_excel(writer, sheet_name="Equity Curve")

            # Returns sheet
            returns_df = self.generate_returns_data()
            returns_df.to_excel(writer, sheet_name="Returns")

            # Trades sheet
            if include_trades and not self.result.trades.empty:
                trade_log = self.generate_trade_log()
                trade_log.to_excel(writer, sheet_name="Trades")

            # Monthly returns sheet
            monthly_df = self.generate_monthly_returns()
            monthly_df.to_excel(writer, sheet_name="Monthly Returns")

            # Benchmark comparison
            benchmark_df = self.generate_benchmark_comparison()
            if benchmark_df is not None:
                benchmark_df.to_excel(writer, sheet_name="Benchmark Comparison")

        logger.info(f"Exported results to {output_file}")
        return output_file

    def _serialize_metrics(self, metrics: dict) -> dict:
        """Serialize metrics for JSON export."""
        serialized = {}

        for key, value in metrics.items():
            if isinstance(value, (pd.Timestamp, datetime)):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_metrics(value)
            elif pd.isna(value):
                serialized[key] = None
            else:
                serialized[key] = value

        return serialized

    @staticmethod
    def compare_backtests(
        results: Dict[str, BacktestResult],
        output_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Compare multiple backtest results.

        Args:
            results: Dictionary mapping names to BacktestResult objects
            output_path: Optional path to save comparison

        Returns:
            DataFrame with comparison metrics

        Example:
            >>> results = {
            ...     'Strategy A': result_a,
            ...     'Strategy B': result_b,
            ... }
            >>> comparison = BacktestReport.compare_backtests(results)
        """
        comparison_data = []

        for name, result in results.items():
            metrics = result.metrics

            comparison_data.append(
                {
                    "Strategy": name,
                    "Ticker": result.ticker,
                    "Total Return (%)": metrics["total_return"],
                    "CAGR (%)": metrics["cagr"],
                    "Sharpe Ratio": metrics["sharpe_ratio"],
                    "Sortino Ratio": metrics["sortino_ratio"],
                    "Max Drawdown (%)": metrics["max_drawdown"],
                    "Volatility (%)": metrics["volatility"],
                    "Win Rate (%)": metrics["win_rate"],
                    "Total Trades": metrics["total_trades"],
                    "Profit Factor": metrics["profit_factor"],
                }
            )

        df = pd.DataFrame(comparison_data)

        if output_path:
            output_file = Path(output_path)
            if output_file.suffix == ".csv":
                df.to_csv(output_file, index=False)
            elif output_file.suffix in [".xlsx", ".xls"]:
                df.to_excel(output_file, index=False)
            else:
                df.to_csv(output_file.with_suffix(".csv"), index=False)

            logger.info(f"Saved comparison to {output_file}")

        return df

    @staticmethod
    def generate_report_html(
        result: BacktestResult,
        output_path: str,
    ) -> Path:
        """
        Generate an HTML report (basic version without plotting library).

        Args:
            result: Backtest result
            output_path: Output file path

        Returns:
            Path to generated HTML file
        """
        output_file = Path(output_path).with_suffix(".html")

        report = BacktestReport(result)

        # Generate HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Report - {result.ticker}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #555;
                    margin-top: 30px;
                }}
                .metric {{
                    display: inline-block;
                    margin: 10px 20px 10px 0;
                    padding: 10px;
                    background-color: #f9f9f9;
                    border-left: 3px solid #4CAF50;
                }}
                .metric-label {{
                    font-weight: bold;
                    color: #666;
                }}
                .metric-value {{
                    font-size: 1.2em;
                    color: #333;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #4CAF50;
                    color: white;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .positive {{
                    color: green;
                }}
                .negative {{
                    color: red;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Backtest Report: {result.ticker}</h1>
                <p>Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}</p>

                <h2>Performance Metrics</h2>
                <div class="metric">
                    <div class="metric-label">Total Return</div>
                    <div class="metric-value {'positive' if result.metrics['total_return'] > 0 else 'negative'}">
                        {result.metrics['total_return']:.2f}%
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">CAGR</div>
                    <div class="metric-value">{result.metrics['cagr']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">{result.metrics['sharpe_ratio']:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value negative">{result.metrics['max_drawdown']:.2f}%</div>
                </div>

                <h2>Trade Statistics</h2>
                <div class="metric">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value">{result.metrics['total_trades']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value">{result.metrics['win_rate']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Profit Factor</div>
                    <div class="metric-value">{result.metrics['profit_factor']:.2f}</div>
                </div>

                <h2>Recent Trades</h2>
        """

        # Add trade table if trades exist
        if not result.trades.empty:
            trade_log = report.generate_trade_log()
            recent_trades = trade_log.tail(20)

            html_content += "<table><thead><tr>"
            html_content += "<th>Date</th><th>Ticker</th><th>Direction</th><th>Shares</th><th>Price</th><th>P&L</th>"
            html_content += "</tr></thead><tbody>"

            for idx, trade in recent_trades.iterrows():
                pnl_class = (
                    "positive" if trade.get("pnl", 0) > 0 else "negative"
                )
                html_content += f"""
                <tr>
                    <td>{idx.strftime('%Y-%m-%d')}</td>
                    <td>{trade['ticker']}</td>
                    <td>{trade['direction']}</td>
                    <td>{trade['shares']:.2f}</td>
                    <td>${trade['price']:.2f}</td>
                    <td class="{pnl_class}">${trade.get('pnl', 0):.2f}</td>
                </tr>
                """

            html_content += "</tbody></table>"
        else:
            html_content += "<p>No trades executed during this period.</p>"

        html_content += """
            </div>
        </body>
        </html>
        """

        # Write HTML file
        with open(output_file, "w") as f:
            f.write(html_content)

        logger.info(f"Generated HTML report: {output_file}")
        return output_file
