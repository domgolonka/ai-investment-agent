#!/usr/bin/env python3
"""
Portfolio Tracking Module Demo

This example demonstrates the comprehensive portfolio tracking capabilities
of the AI Investment Agent, including:
- Creating and managing positions
- Recording transactions (buys, sells, dividends)
- Calculating P&L and performance metrics
- Multi-currency support
- Persistent storage with SQLite
- CSV export/import

Run this script to see the portfolio module in action.
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.portfolio import (
    Position,
    Transaction,
    TransactionType,
    PortfolioManager,
    PnLCalculator,
    PortfolioStorage,
    create_buy_transaction,
    create_sell_transaction,
    create_dividend_transaction
)


def demo_basic_portfolio():
    """Demonstrate basic portfolio creation and position management."""
    print("=" * 80)
    print("DEMO 1: Basic Portfolio Creation")
    print("=" * 80)

    # Create a portfolio manager
    manager = PortfolioManager(name="Demo Portfolio", base_currency="USD")
    print(f"\n✓ Created portfolio: {manager.name}")

    # Add some positions
    positions_to_add = [
        ("AAPL", 100, 150.0, "USD"),
        ("MSFT", 50, 300.0, "USD"),
        ("1681.HK", 2000, 50.0, "HKD"),  # Hong Kong stock
    ]

    for ticker, shares, avg_cost, currency in positions_to_add:
        position = Position(
            ticker=ticker,
            shares=shares,
            avg_cost=avg_cost,
            currency=currency,
            purchase_date=datetime.now() - timedelta(days=90)
        )
        manager.add_position(position)
        print(f"  Added: {ticker} - {shares} shares @ {avg_cost} {currency}")

    # Update current prices
    print("\n✓ Updating current prices...")
    manager.update_position_price("AAPL", 175.0)
    manager.update_position_price("MSFT", 350.0)
    manager.update_position_price("1681.HK", 55.0)

    # Display positions
    print("\n📊 Current Positions:")
    for ticker, position in manager.positions.items():
        print(f"  {ticker:10s} | {position.shares:8.2f} shares | "
              f"Cost: {position.total_cost:10.2f} {position.currency} | "
              f"Value: {position.current_value:10.2f} {position.currency} | "
              f"P&L: {position.unrealized_pnl:+10.2f} ({position.unrealized_pnl_pct:+6.2f}%)")

    # Get portfolio summary
    summary = manager.get_positions_summary()
    print(f"\n💰 Portfolio Summary:")
    print(f"  Total Positions: {summary['total_positions']}")
    print(f"  Total Value: {summary['total_value']:.2f}")
    print(f"  Total Cost: {summary['total_cost']:.2f}")
    print(f"  Total P&L: {summary['total_pnl']:+.2f} ({summary['total_pnl_pct']:+.2f}%)")

    return manager


def demo_transactions(manager: PortfolioManager):
    """Demonstrate transaction recording."""
    print("\n" + "=" * 80)
    print("DEMO 2: Recording Transactions")
    print("=" * 80)

    # Record a buy transaction (adding to existing position)
    print("\n✓ Recording transactions...")
    buy_txn = create_buy_transaction(
        ticker="AAPL",
        shares=50,
        price=160.0,
        date=datetime.now() - timedelta(days=30),
        fees=5.0,
        notes="Added to position"
    )
    manager.record_transaction(buy_txn)
    print(f"  BUY: {buy_txn}")

    # Record a sell transaction
    sell_txn = create_sell_transaction(
        ticker="MSFT",
        shares=20,
        price=360.0,
        date=datetime.now() - timedelta(days=10),
        fees=5.0,
        notes="Partial exit"
    )
    manager.record_transaction(sell_txn)
    print(f"  SELL: {sell_txn}")

    # Record dividend transactions
    dividend_txn = create_dividend_transaction(
        ticker="AAPL",
        dividend_amount=100.0,
        date=datetime.now() - timedelta(days=5),
        notes="Quarterly dividend"
    )
    manager.record_transaction(dividend_txn)
    print(f"  DIVIDEND: {dividend_txn}")

    # Display transaction history
    print("\n📝 Transaction History:")
    for txn in manager.get_transactions():
        print(f"  {txn.date.date()} | {txn.ticker:10s} | {txn.transaction_type.value:8s} | "
              f"Amount: {txn.total_amount:10.2f} {txn.currency}")


def demo_pnl_calculation(manager: PortfolioManager):
    """Demonstrate P&L calculations."""
    print("\n" + "=" * 80)
    print("DEMO 3: P&L Calculations")
    print("=" * 80)

    calculator = PnLCalculator(manager)

    # Calculate realized P&L
    print("\n✓ Realized P&L (from closed positions):")
    realized = calculator.calculate_realized_pnl()
    print(f"  Total Realized P&L: ${realized['total_realized_pnl']:+.2f}")
    print(f"  Total Proceeds: ${realized['total_proceeds']:.2f}")
    print(f"  Total Cost Basis: ${realized['total_cost_basis']:.2f}")
    print(f"  Transactions: {realized['transaction_count']}")

    if realized['by_ticker']:
        print(f"\n  By Ticker:")
        for ticker, pnl in realized['by_ticker'].items():
            print(f"    {ticker}: ${pnl:+.2f}")

    # Calculate unrealized P&L
    print("\n✓ Unrealized P&L (from open positions):")
    unrealized = calculator.calculate_unrealized_pnl()
    print(f"  Total Unrealized P&L: ${unrealized['total_unrealized_pnl']:+.2f}")
    print(f"  Total Unrealized %: {unrealized['total_unrealized_pnl_pct']:+.2f}%")
    print(f"  Market Value: ${unrealized['total_market_value']:.2f}")
    print(f"  Cost Basis: ${unrealized['total_cost_basis']:.2f}")

    if unrealized['by_ticker']:
        print(f"\n  By Ticker:")
        for ticker, pnl in unrealized['by_ticker'].items():
            position = manager.get_position(ticker)
            pnl_pct = position.unrealized_pnl_pct or 0
            print(f"    {ticker}: ${pnl:+.2f} ({pnl_pct:+.2f}%)")

    # Calculate total return
    print("\n✓ Total Return (realized + unrealized + dividends):")
    total = calculator.calculate_total_return()
    print(f"  Total Return: ${total['total_return']:+.2f}")
    print(f"  Total Return %: {total['total_return_pct']:+.2f}%")
    print(f"  Realized P&L: ${total['realized_pnl']:+.2f}")
    print(f"  Unrealized P&L: ${total['unrealized_pnl']:+.2f}")
    print(f"  Dividend Income: ${total['dividend_income']:.2f}")

    # Get comprehensive metrics
    print("\n✓ Portfolio Metrics:")
    metrics = calculator.calculate_portfolio_metrics()
    print(f"  Total Invested: ${metrics['total_invested']:.2f}")
    print(f"  Current Value: ${metrics['current_value']:.2f}")
    print(f"  Total Return: ${metrics['total_return']:+.2f} ({metrics['total_return_pct']:+.2f}%)")
    print(f"  Total Positions: {metrics['total_positions']}")
    print(f"  Total Transactions: {metrics['total_transactions']}")

    if metrics['best_performer']:
        print(f"\n  🏆 Best Performer: {metrics['best_performer']['ticker']} "
              f"({metrics['best_performer']['pnl_pct']:+.2f}%)")
    if metrics['worst_performer']:
        print(f"  📉 Worst Performer: {metrics['worst_performer']['ticker']} "
              f"({metrics['worst_performer']['pnl_pct']:+.2f}%)")

    # Win rate
    print("\n✓ Win Rate Analysis:")
    win_stats = calculator.calculate_win_rate()
    if win_stats['total_closed_positions'] > 0:
        print(f"  Closed Positions: {win_stats['total_closed_positions']}")
        print(f"  Wins: {win_stats['wins']}")
        print(f"  Losses: {win_stats['losses']}")
        print(f"  Win Rate: {win_stats['win_rate']:.1f}%")
        if win_stats['avg_win'] > 0:
            print(f"  Average Win: ${win_stats['avg_win']:.2f}")
        if win_stats['avg_loss'] < 0:
            print(f"  Average Loss: ${win_stats['avg_loss']:.2f}")
        if win_stats['profit_factor'] != float('inf'):
            print(f"  Profit Factor: {win_stats['profit_factor']:.2f}")
    else:
        print(f"  No closed positions yet")


def demo_storage(manager: PortfolioManager):
    """Demonstrate persistent storage."""
    print("\n" + "=" * 80)
    print("DEMO 4: Persistent Storage")
    print("=" * 80)

    # Create storage
    storage = PortfolioStorage("demo_portfolio.db")

    # Save portfolio
    print("\n✓ Saving portfolio to database...")
    storage.save_portfolio(manager)
    print(f"  Saved: {len(manager.positions)} positions, {len(manager.transactions)} transactions")

    # List portfolios
    print("\n✓ Available portfolios:")
    for portfolio_name in storage.list_portfolios():
        print(f"  - {portfolio_name}")

    # Load portfolio
    print("\n✓ Loading portfolio from database...")
    loaded_manager = storage.load_portfolio(manager.name)
    print(f"  Loaded: {len(loaded_manager.positions)} positions, {len(loaded_manager.transactions)} transactions")

    # Verify data
    print("\n✓ Verification:")
    print(f"  Original positions: {len(manager.positions)}")
    print(f"  Loaded positions: {len(loaded_manager.positions)}")
    print(f"  Original transactions: {len(manager.transactions)}")
    print(f"  Loaded transactions: {len(loaded_manager.transactions)}")

    # Export to CSV
    print("\n✓ Exporting to CSV...")
    files = storage.export_to_csv(manager.name, output_dir=".")
    print(f"  Positions CSV: {files['positions']}")
    print(f"  Transactions CSV: {files['transactions']}")

    return storage


def demo_multi_currency(manager: PortfolioManager):
    """Demonstrate multi-currency support."""
    print("\n" + "=" * 80)
    print("DEMO 5: Multi-Currency Support")
    print("=" * 80)

    # Group positions by currency
    print("\n✓ Positions by Currency:")
    by_currency = manager.get_positions_by_currency()
    for currency, positions in by_currency.items():
        total_value = sum(p.current_value or 0 for p in positions)
        total_cost = sum(p.total_cost for p in positions)
        pnl = total_value - total_cost
        pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0

        print(f"\n  {currency}:")
        print(f"    Positions: {len(positions)}")
        print(f"    Total Value: {total_value:.2f} {currency}")
        print(f"    Total Cost: {total_cost:.2f} {currency}")
        print(f"    P&L: {pnl:+.2f} {currency} ({pnl_pct:+.2f}%)")

        for position in positions:
            print(f"      - {position.ticker}: {position.shares:.2f} shares @ "
                  f"{position.avg_cost:.2f} {currency}")


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("Portfolio Tracking Module Demo")
    print("=" * 80)

    # Run demos
    manager = demo_basic_portfolio()
    demo_transactions(manager)
    demo_pnl_calculation(manager)
    demo_multi_currency(manager)
    storage = demo_storage(manager)

    print("\n" + "=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("  ✓ Position tracking with real-time P&L")
    print("  ✓ Transaction recording (BUY, SELL, DIVIDEND)")
    print("  ✓ Comprehensive P&L calculations")
    print("  ✓ Multi-currency support")
    print("  ✓ Persistent storage with SQLite")
    print("  ✓ CSV export/import")
    print("\nDatabase file: demo_portfolio.db")
    print("CSV files: Demo_Portfolio_positions.csv, Demo_Portfolio_transactions.csv")


if __name__ == "__main__":
    main()
