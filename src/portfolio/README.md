# Portfolio Tracking Module

Comprehensive portfolio management system for the AI Investment Agent with real-time P&L tracking, multi-currency support, and persistent storage.

## Features

- **Position Management**: Track individual stock positions with real-time pricing and P&L
- **Transaction Recording**: Complete transaction history (BUY, SELL, DIVIDEND)
- **Multi-Currency Support**: Handle positions in different currencies (USD, HKD, JPY, etc.)
- **P&L Calculations**: Realized and unrealized gains, total returns, win rates
- **Persistent Storage**: SQLite database with automatic save/load
- **CSV Export/Import**: Easy data portability
- **Performance Metrics**: Comprehensive portfolio analytics

## Quick Start

```python
from datetime import datetime
from src.portfolio import (
    Position,
    PortfolioManager,
    PnLCalculator,
    PortfolioStorage,
    create_buy_transaction,
    create_sell_transaction
)

# Create a portfolio
manager = PortfolioManager(name="My Portfolio")

# Add a position
position = Position(
    ticker="AAPL",
    shares=100,
    avg_cost=150.0,
    currency="USD",
    purchase_date=datetime.now()
)
manager.add_position(position)

# Update current price
manager.update_position_price("AAPL", 175.0)

# Check P&L
print(position.unrealized_pnl)  # +2500.0
print(position.unrealized_pnl_pct)  # +16.67%

# Record a transaction
buy = create_buy_transaction("AAPL", 50, 160.0, datetime.now())
manager.record_transaction(buy)

# Calculate portfolio metrics
calculator = PnLCalculator(manager)
metrics = calculator.calculate_portfolio_metrics()
print(f"Total Return: ${metrics['total_return']:.2f}")

# Save to database
storage = PortfolioStorage("portfolio.db")
storage.save_portfolio(manager)
```

## Module Structure

```
src/portfolio/
├── __init__.py         # Module exports
├── position.py         # Position dataclass
├── transaction.py      # Transaction tracking
├── manager.py          # Portfolio manager
├── pnl.py             # P&L calculations
├── storage.py         # Persistent storage
└── README.md          # This file
```

## Core Classes

### Position

Represents a single stock position with P&L tracking.

```python
position = Position(
    ticker="AAPL",
    shares=100,
    avg_cost=150.0,
    currency="USD",
    purchase_date=datetime.now()
)

# Update price
position.update_price(175.0)

# Add shares
position.add_shares(50, 160.0)

# Remove shares
cost = position.remove_shares(30)
```

**Key Attributes**:
- `ticker`: Stock symbol
- `shares`: Number of shares
- `avg_cost`: Average cost per share
- `current_price`: Current market price
- `unrealized_pnl`: Unrealized profit/loss
- `unrealized_pnl_pct`: P&L percentage

### Transaction

Records portfolio activity (buys, sells, dividends).

```python
from src.portfolio import TransactionType, create_buy_transaction

# Create transactions
buy = create_buy_transaction("AAPL", 100, 150.0, datetime.now(), fees=5.0)
sell = create_sell_transaction("AAPL", 50, 175.0, datetime.now(), fees=5.0)
div = create_dividend_transaction("AAPL", 100.0, datetime.now())
```

**Transaction Types**:
- `BUY`: Purchase shares
- `SELL`: Sell shares
- `DIVIDEND`: Dividend payment

### PortfolioManager

Central manager for positions and transactions.

```python
manager = PortfolioManager(name="My Portfolio", base_currency="USD")

# Add/remove positions
manager.add_position(position)
manager.remove_position("AAPL")

# Update prices
manager.update_position_price("AAPL", 175.0)

# Record transactions
manager.record_transaction(buy_transaction)

# Get positions
position = manager.get_position("AAPL")
all_positions = manager.positions

# Get transactions
all_txns = manager.get_transactions()
aapl_txns = manager.get_transactions(ticker="AAPL")
buys = manager.get_transactions(transaction_type=TransactionType.BUY)

# Portfolio metrics
total_value = manager.get_total_value()
total_cost = manager.get_total_cost()
pnl, pnl_pct = manager.get_total_pnl()

# Group by currency
by_currency = manager.get_positions_by_currency()
usd_positions = by_currency["USD"]

# Summary
summary = manager.get_positions_summary()
```

### PnLCalculator

Calculate performance metrics.

```python
calculator = PnLCalculator(manager)

# Realized P&L (from sold positions)
realized = calculator.calculate_realized_pnl()
print(f"Realized P&L: ${realized['total_realized_pnl']:.2f}")

# Unrealized P&L (from open positions)
unrealized = calculator.calculate_unrealized_pnl()
print(f"Unrealized P&L: ${unrealized['total_unrealized_pnl']:.2f}")

# Total return (realized + unrealized + dividends)
total = calculator.calculate_total_return()
print(f"Total Return: ${total['total_return']:.2f} ({total['total_return_pct']:.2f}%)")

# Comprehensive metrics
metrics = calculator.calculate_portfolio_metrics()
print(f"Best Performer: {metrics['best_performer']}")
print(f"Worst Performer: {metrics['worst_performer']}")

# Win rate analysis
win_stats = calculator.calculate_win_rate()
print(f"Win Rate: {win_stats['win_rate']:.1f}%")

# Time period returns
ytd_return = calculator.calculate_time_period_return(
    start_date=datetime(2024, 1, 1)
)
```

### PortfolioStorage

Persistent storage with SQLite and CSV export.

```python
storage = PortfolioStorage("portfolio.db")

# Save portfolio
storage.save_portfolio(manager)

# Load portfolio
manager = storage.load_portfolio("My Portfolio")

# List portfolios
portfolios = storage.list_portfolios()

# Delete portfolio
storage.delete_portfolio("Old Portfolio")

# Export to CSV
files = storage.export_to_csv("My Portfolio", output_dir=".")
# Creates: My_Portfolio_positions.csv, My_Portfolio_transactions.csv

# Import from CSV
manager = storage.import_from_csv(
    "Imported Portfolio",
    positions_file="positions.csv",
    transactions_file="transactions.csv"
)
```

## Multi-Currency Support

The module handles positions in different currencies:

```python
# Create positions in different currencies
aapl = Position("AAPL", 100, 150.0, "USD", datetime.now())
hsbc = Position("1681.HK", 2000, 50.0, "HKD", datetime.now())
toyota = Position("7203.T", 100, 2500.0, "JPY", datetime.now())

manager.add_position(aapl)
manager.add_position(hsbc)
manager.add_position(toyota)

# Group by currency
by_currency = manager.get_positions_by_currency()

for currency, positions in by_currency.items():
    total_value = sum(p.current_value or 0 for p in positions)
    print(f"{currency}: {total_value:.2f}")
```

**Note**: Values are tracked in their native currencies. For cross-currency aggregation, you'll need to apply FX rates using the project's `fx_normalization` module.

## Error Handling

The module uses the project's exception hierarchy:

```python
from src.portfolio import (
    PortfolioError,
    PositionNotFoundError,
    InsufficientSharesError,
    StorageError
)

try:
    manager.remove_position("INVALID")
except PositionNotFoundError as e:
    print(f"Position not found: {e}")

try:
    sell = create_sell_transaction("AAPL", 1000, 175.0, datetime.now())
    manager.record_transaction(sell)
except InsufficientSharesError as e:
    print(f"Not enough shares: {e}")
```

## Examples

See `/Users/dom-personal/PycharmProjects/ai-investment-agent/examples/portfolio_demo.py` for comprehensive examples including:

- Basic portfolio creation and management
- Transaction recording (BUY, SELL, DIVIDEND)
- P&L calculations
- Multi-currency support
- Persistent storage
- CSV export/import

Run the demo:
```bash
python3 examples/portfolio_demo.py
```

## Database Schema

SQLite tables:

```sql
-- Portfolios
CREATE TABLE portfolios (
    name TEXT PRIMARY KEY,
    base_currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Positions
CREATE TABLE positions (
    portfolio_name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    shares REAL NOT NULL,
    avg_cost REAL NOT NULL,
    currency TEXT NOT NULL,
    purchase_date TEXT NOT NULL,
    current_price REAL,
    last_updated TEXT,
    notes TEXT,
    PRIMARY KEY (portfolio_name, ticker),
    FOREIGN KEY (portfolio_name) REFERENCES portfolios(name)
);

-- Transactions
CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    portfolio_name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    shares REAL NOT NULL,
    price REAL NOT NULL,
    fees REAL NOT NULL,
    date TEXT NOT NULL,
    currency TEXT NOT NULL,
    notes TEXT,
    dividend_amount REAL,
    FOREIGN KEY (portfolio_name) REFERENCES portfolios(name)
);
```

## Integration with AI Investment Agent

The portfolio module integrates with other agent components:

```python
from src.portfolio import PortfolioManager, PnLCalculator
from src.fx_normalization import normalize_to_usd

# Create portfolio
manager = PortfolioManager(name="AI Agent Portfolio")

# Normalize multi-currency portfolio to USD
async def get_portfolio_value_usd():
    total_usd = 0.0

    for position in manager.positions.values():
        if position.current_value:
            # Use FX normalization for cross-currency
            value_usd, meta = await normalize_to_usd(
                position.current_value,
                position.currency,
                metric_name=f"{position.ticker}_value"
            )
            if value_usd:
                total_usd += value_usd

    return total_usd
```

## Performance Considerations

- **Position Updates**: O(1) for individual position updates
- **Portfolio Aggregations**: O(n) where n = number of positions
- **Transaction Queries**: Indexed by portfolio, ticker, and date
- **Storage**: SQLite with proper indices for fast queries
- **Memory**: Lightweight - all positions and transactions held in memory

## Future Enhancements

Potential additions (not yet implemented):

- Integration with real-time price feeds (yfinance, EODHD)
- Automatic FX conversion for cross-currency reporting
- Tax lot tracking (FIFO, LIFO, specific identification)
- Performance attribution analysis
- Benchmark comparison (S&P 500, etc.)
- Risk metrics (Sharpe ratio, max drawdown, volatility)
- Asset allocation analysis
- Rebalancing recommendations

## License

Part of the AI Investment Agent project. See main project LICENSE.
