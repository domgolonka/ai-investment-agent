#!/usr/bin/env python3
"""
Verification script for the backtesting framework.

This script verifies that:
1. All modules can be imported
2. Basic functionality works
3. No critical errors in the framework
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_imports():
    """Verify all backtesting modules can be imported."""
    print("Verifying imports...")

    try:
        from src.backtesting import (
            BacktestConfig,
            BacktestEngine,
            BacktestReport,
            BacktestResult,
            HistoricalDataLoader,
            PerformanceMetrics,
            Position,
            SimulatedPortfolio,
            Trade,
        )

        print("  All imports successful")
        return True
    except ImportError as e:
        print(f"  Import error: {e}")
        return False


def verify_basic_functionality():
    """Verify basic functionality of each component."""
    print("\nVerifying basic functionality...")

    try:
        from src.backtesting import (
            BacktestConfig,
            BacktestEngine,
            HistoricalDataLoader,
            PerformanceMetrics,
            SimulatedPortfolio,
        )

        # Test config creation
        config = BacktestConfig(initial_capital=100000.0)
        print(f"  Config created: ${config.initial_capital:,.2f} initial capital")

        # Test portfolio creation
        portfolio = SimulatedPortfolio(initial_capital=100000.0)
        print(f"  Portfolio created: ${portfolio.cash:,.2f} cash")

        # Test metrics calculator
        metrics = PerformanceMetrics(risk_free_rate=0.02)
        print(f"  Metrics calculator created: {metrics.risk_free_rate:.2%} risk-free rate")

        # Test data loader
        loader = HistoricalDataLoader()
        print(f"  Data loader created: cache_enabled={loader.config.cache_enabled}")

        # Test engine
        engine = BacktestEngine(config=config)
        print(f"  Engine created: ${engine.config.initial_capital:,.2f} initial capital")

        print("  Basic functionality verified")
        return True

    except Exception as e:
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_class_structure():
    """Verify class structure and methods."""
    print("\nVerifying class structure...")

    try:
        from src.backtesting import BacktestEngine, PerformanceMetrics, SimulatedPortfolio

        # Check BacktestEngine methods
        engine_methods = [
            "run_backtest",
            "simulate_signals",
            "calculate_returns",
            "run_multiple_backtests",
            "optimize_parameters",
        ]
        for method in engine_methods:
            assert hasattr(
                BacktestEngine, method
            ), f"BacktestEngine missing {method}"

        print(f"  BacktestEngine has all {len(engine_methods)} required methods")

        # Check SimulatedPortfolio methods
        portfolio_methods = [
            "execute_trade",
            "get_portfolio_value",
            "get_holdings",
            "update_prices",
            "get_portfolio_history",
            "get_trade_log",
        ]
        for method in portfolio_methods:
            assert hasattr(
                SimulatedPortfolio, method
            ), f"SimulatedPortfolio missing {method}"

        print(f"  SimulatedPortfolio has all {len(portfolio_methods)} required methods")

        # Check PerformanceMetrics methods
        metrics_methods = [
            "calculate_sharpe_ratio",
            "calculate_sortino_ratio",
            "calculate_max_drawdown",
            "calculate_win_rate",
            "calculate_cagr",
            "calculate_volatility",
            "compare_to_benchmark",
        ]
        for method in metrics_methods:
            assert hasattr(
                PerformanceMetrics, method
            ), f"PerformanceMetrics missing {method}"

        print(f"  PerformanceMetrics has all {len(metrics_methods)} required methods")

        print("  Class structure verified")
        return True

    except AssertionError as e:
        print(f"  Assertion error: {e}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_exception_handling():
    """Verify exception handling."""
    print("\nVerifying exception handling...")

    try:
        from src.backtesting import BacktestConfig
        from src.exceptions import DataValidationError

        # Test invalid config raises proper exception
        try:
            config = BacktestConfig(initial_capital=-1000.0)
            print("  ERROR: Invalid config did not raise exception")
            return False
        except DataValidationError:
            print("  Invalid initial capital properly raises DataValidationError")

        try:
            config = BacktestConfig(position_size=1.5)
            print("  ERROR: Invalid position size did not raise exception")
            return False
        except DataValidationError:
            print("  Invalid position size properly raises DataValidationError")

        print("  Exception handling verified")
        return True

    except Exception as e:
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("BACKTESTING FRAMEWORK VERIFICATION")
    print("=" * 60)

    results = []

    # Run verification tests
    results.append(("Imports", verify_imports()))
    results.append(("Basic Functionality", verify_basic_functionality()))
    results.append(("Class Structure", verify_class_structure()))
    results.append(("Exception Handling", verify_exception_handling()))

    # Print results
    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\nAll verifications PASSED")
        print("\nThe backtesting framework is ready to use!")
        print("\nNext steps:")
        print("  1. Run: python examples/backtest_example.py")
        print("  2. Run: pytest tests/test_backtesting.py")
        print("  3. See: src/backtesting/README.md for documentation")
        return 0
    else:
        print("\nSome verifications FAILED")
        print("Please check the errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
