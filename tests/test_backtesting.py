"""
Unit tests for the backtesting framework.

Tests cover:
- Data loading and caching
- Portfolio simulation
- Performance metrics calculation
- Backtest engine execution
- Report generation
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.backtesting import (
    BacktestConfig,
    BacktestEngine,
    BacktestReport,
    HistoricalDataLoader,
    PerformanceMetrics,
    Position,
    SimulatedPortfolio,
    Trade,
)
from src.backtesting.portfolio import TradeDirection
from src.exceptions import DataValidationError


class TestHistoricalDataLoader:
    """Test the HistoricalDataLoader class."""

    def test_load_price_data(self):
        """Test loading historical price data."""
        loader = HistoricalDataLoader()

        data = loader.load_price_data(
            ticker="AAPL", start_date="2024-01-01", end_date="2024-01-31"
        )

        assert not data.empty
        assert "Close" in data.columns
        assert "Open" in data.columns
        assert "High" in data.columns
        assert "Low" in data.columns
        assert "Volume" in data.columns

    def test_data_validation(self):
        """Test data validation catches invalid data."""
        loader = HistoricalDataLoader()

        # Test with invalid ticker that returns no data
        with pytest.raises(Exception):  # DataFetchError or similar
            loader.load_price_data(
                ticker="INVALID_TICKER_XYZ123",
                start_date="2024-01-01",
                end_date="2024-01-31",
            )

    def test_resample_data(self):
        """Test data resampling."""
        loader = HistoricalDataLoader()

        daily_data = loader.load_price_data(
            ticker="AAPL", start_date="2024-01-01", end_date="2024-01-31"
        )

        weekly_data = loader.resample_data(daily_data, "W")

        assert len(weekly_data) < len(daily_data)
        assert "Close" in weekly_data.columns


class TestSimulatedPortfolio:
    """Test the SimulatedPortfolio class."""

    def test_portfolio_initialization(self):
        """Test portfolio initialization."""
        portfolio = SimulatedPortfolio(initial_capital=100000.0)

        assert portfolio.cash == 100000.0
        assert len(portfolio.positions) == 0
        assert len(portfolio.trades) == 0

    def test_buy_trade(self):
        """Test buying shares."""
        portfolio = SimulatedPortfolio(initial_capital=100000.0)

        trade = portfolio.execute_trade(
            ticker="AAPL",
            signal="BUY",
            price=150.0,
            date=datetime(2024, 1, 1),
            position_size=0.1,
        )

        assert trade is not None
        assert trade.direction == TradeDirection.BUY
        assert "AAPL" in portfolio.positions
        assert portfolio.cash < 100000.0

    def test_sell_trade(self):
        """Test selling shares."""
        portfolio = SimulatedPortfolio(initial_capital=100000.0)

        # Buy first
        portfolio.execute_trade(
            ticker="AAPL",
            signal="BUY",
            price=150.0,
            date=datetime(2024, 1, 1),
            position_size=0.5,
        )

        cash_after_buy = portfolio.cash

        # Then sell
        trade = portfolio.execute_trade(
            ticker="AAPL",
            signal="SELL",
            price=160.0,
            date=datetime(2024, 1, 2),
        )

        assert trade is not None
        assert trade.direction == TradeDirection.SELL
        assert portfolio.cash > cash_after_buy

    def test_portfolio_value(self):
        """Test portfolio value calculation."""
        portfolio = SimulatedPortfolio(initial_capital=100000.0)

        # Buy shares
        portfolio.execute_trade(
            ticker="AAPL",
            signal="BUY",
            price=150.0,
            date=datetime(2024, 1, 1),
            position_size=0.5,
        )

        # Update price
        portfolio.update_prices({"AAPL": 160.0}, datetime(2024, 1, 2))

        # Get portfolio value
        value = portfolio.get_portfolio_value(datetime(2024, 1, 2))

        assert value > 100000.0  # Price increased

    def test_commission_calculation(self):
        """Test commission is properly calculated."""
        portfolio = SimulatedPortfolio(
            initial_capital=100000.0, commission_rate=0.001, min_commission=1.0
        )

        initial_cash = portfolio.cash

        trade = portfolio.execute_trade(
            ticker="AAPL",
            signal="BUY",
            price=150.0,
            date=datetime(2024, 1, 1),
            shares=100.0,
        )

        assert trade.commission > 0
        expected_cash = initial_cash - (100 * 150.0) - trade.commission
        assert abs(portfolio.cash - expected_cash) < 0.01


class TestPerformanceMetrics:
    """Test the PerformanceMetrics class."""

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        metrics = PerformanceMetrics()

        # Create sample returns
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005] * 50)

        sharpe = metrics.calculate_sharpe_ratio(returns)

        assert isinstance(sharpe, float)
        assert not pd.isna(sharpe)

    def test_sortino_ratio(self):
        """Test Sortino ratio calculation."""
        metrics = PerformanceMetrics()

        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005] * 50)

        sortino = metrics.calculate_sortino_ratio(returns)

        assert isinstance(sortino, float)
        assert not pd.isna(sortino)

    def test_max_drawdown(self):
        """Test max drawdown calculation."""
        metrics = PerformanceMetrics()

        # Create equity curve with a drawdown
        equity = pd.Series([100, 110, 120, 100, 90, 95, 110, 115])

        max_dd, peak, trough = metrics.calculate_max_drawdown(equity)

        assert max_dd > 0
        assert peak is not None
        assert trough is not None

    def test_cagr(self):
        """Test CAGR calculation."""
        metrics = PerformanceMetrics()

        # Create equity curve over 1 year
        dates = pd.date_range("2023-01-01", "2024-01-01", freq="D")
        equity = pd.Series(100 * (1.1 ** (pd.Series(range(len(dates))) / 252)), index=dates)

        cagr = metrics.calculate_cagr(equity)

        # CAGR should be approximately 10%
        assert 9.0 < cagr < 11.0

    def test_volatility(self):
        """Test volatility calculation."""
        metrics = PerformanceMetrics()

        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005] * 50)

        volatility = metrics.calculate_volatility(returns)

        assert volatility > 0


class TestBacktestEngine:
    """Test the BacktestEngine class."""

    def test_engine_initialization(self):
        """Test engine initialization."""
        config = BacktestConfig(initial_capital=100000.0)
        engine = BacktestEngine(config=config)

        assert engine.config.initial_capital == 100000.0

    def test_simple_backtest(self):
        """Test running a simple backtest."""

        def simple_strategy(data, date):
            """Always hold."""
            return "HOLD"

        config = BacktestConfig(initial_capital=100000.0, position_size=0.1)
        engine = BacktestEngine(config=config)

        result = engine.run_backtest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            strategy_func=simple_strategy,
        )

        assert result is not None
        assert result.ticker == "AAPL"
        assert "total_return" in result.metrics
        assert len(result.equity_curve) > 0

    def test_buy_and_hold_strategy(self):
        """Test buy and hold strategy."""

        def buy_and_hold(data, date):
            """Buy on first day, hold thereafter."""
            current_idx = data.index.get_loc(date)
            if current_idx == 0:
                return "BUY"
            return "HOLD"

        config = BacktestConfig(initial_capital=100000.0, position_size=0.5)
        engine = BacktestEngine(config=config)

        result = engine.run_backtest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            strategy_func=buy_and_hold,
        )

        assert len(result.trades) >= 1
        assert result.portfolio.cash < 100000.0  # Cash was used to buy

    def test_backtest_with_signals(self):
        """Test backtest with pre-computed signals."""
        config = BacktestConfig(initial_capital=100000.0)
        engine = BacktestEngine(config=config)

        # Load data to get dates
        loader = HistoricalDataLoader()
        data = loader.load_price_data(
            ticker="AAPL", start_date="2024-01-01", end_date="2024-01-31"
        )

        # Create signals
        signals = pd.Series(index=data.index, data="HOLD")
        signals.iloc[0] = "BUY"  # Buy on first day

        result = engine.run_backtest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            signals=signals,
        )

        assert result is not None
        assert len(result.trades) >= 1


class TestBacktestReport:
    """Test the BacktestReport class."""

    def test_generate_summary(self):
        """Test summary generation."""

        def simple_strategy(data, date):
            return "HOLD"

        config = BacktestConfig(initial_capital=100000.0)
        engine = BacktestEngine(config=config)

        result = engine.run_backtest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            strategy_func=simple_strategy,
        )

        report = BacktestReport(result)
        summary = report.generate_summary()

        assert isinstance(summary, str)
        assert "AAPL" in summary
        assert "Total Return" in summary

    def test_export_json(self):
        """Test JSON export."""

        def simple_strategy(data, date):
            return "HOLD"

        config = BacktestConfig(initial_capital=100000.0)
        engine = BacktestEngine(config=config)

        result = engine.run_backtest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            strategy_func=simple_strategy,
        )

        report = BacktestReport(result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_backtest"
            json_file = report.export_results(output_path, format="json")

            assert json_file.exists()

            # Verify JSON is valid
            with open(json_file) as f:
                data = json.load(f)
                assert "metadata" in data
                assert "metrics" in data

    def test_equity_curve_generation(self):
        """Test equity curve data generation."""

        def simple_strategy(data, date):
            return "HOLD"

        config = BacktestConfig(initial_capital=100000.0)
        engine = BacktestEngine(config=config)

        result = engine.run_backtest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            strategy_func=simple_strategy,
        )

        report = BacktestReport(result)
        equity_df = report.generate_equity_curve()

        assert not equity_df.empty
        assert "portfolio_value" in equity_df.columns
        assert "drawdown_pct" in equity_df.columns


class TestBacktestConfig:
    """Test the BacktestConfig class."""

    def test_valid_config(self):
        """Test creating a valid configuration."""
        config = BacktestConfig(
            initial_capital=100000.0,
            position_size=0.1,
            commission_rate=0.001,
        )

        assert config.initial_capital == 100000.0
        assert config.position_size == 0.1

    def test_invalid_initial_capital(self):
        """Test invalid initial capital raises error."""
        with pytest.raises(DataValidationError):
            BacktestConfig(initial_capital=-1000.0)

    def test_invalid_position_size(self):
        """Test invalid position size raises error."""
        with pytest.raises(DataValidationError):
            BacktestConfig(position_size=1.5)  # > 1

    def test_invalid_commission_rate(self):
        """Test invalid commission rate raises error."""
        with pytest.raises(DataValidationError):
            BacktestConfig(commission_rate=-0.001)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
