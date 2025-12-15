"""
Simulated portfolio for backtesting.

This module provides classes to track portfolio state, execute trades,
and maintain transaction history during backtesting.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import pandas as pd

from src.exceptions import DataValidationError

logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    """Direction of a trade."""

    BUY = "BUY"
    SELL = "SELL"


class TradeType(Enum):
    """Type of trade execution."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


@dataclass
class Trade:
    """
    Represents a single trade execution.

    Attributes:
        ticker: Stock ticker symbol
        direction: BUY or SELL
        shares: Number of shares traded
        price: Execution price per share
        date: Execution datetime
        commission: Trading commission/fees
        trade_type: Type of trade (MARKET, LIMIT, etc.)
        value: Total trade value (shares * price)
        notes: Optional notes about the trade
    """

    ticker: str
    direction: TradeDirection
    shares: float
    price: float
    date: datetime
    commission: float = 0.0
    trade_type: TradeType = TradeType.MARKET
    notes: str = ""

    def __post_init__(self):
        """Calculate derived values."""
        self.value = self.shares * self.price

    @property
    def total_cost(self) -> float:
        """Total cost including commission."""
        if self.direction == TradeDirection.BUY:
            return self.value + self.commission
        else:
            return self.value - self.commission

    def __str__(self) -> str:
        """String representation of trade."""
        return (
            f"{self.direction.value} {self.shares:.2f} {self.ticker} @ "
            f"${self.price:.2f} on {self.date.strftime('%Y-%m-%d')}"
        )


@dataclass
class Position:
    """
    Represents a position in a stock.

    Attributes:
        ticker: Stock ticker symbol
        shares: Number of shares held
        avg_price: Average purchase price per share
        current_price: Current market price per share
        last_update: Last price update datetime
    """

    ticker: str
    shares: float
    avg_price: float
    current_price: float
    last_update: datetime

    @property
    def market_value(self) -> float:
        """Current market value of position."""
        return self.shares * self.current_price

    @property
    def cost_basis(self) -> float:
        """Total cost basis of position."""
        return self.shares * self.avg_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss."""
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_percent(self) -> float:
        """Unrealized profit/loss as percentage."""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    def update_price(self, price: float, date: datetime) -> None:
        """Update current price."""
        self.current_price = price
        self.last_update = date

    def __str__(self) -> str:
        """String representation of position."""
        return (
            f"{self.ticker}: {self.shares:.2f} shares @ ${self.current_price:.2f} "
            f"(avg: ${self.avg_price:.2f}, P&L: {self.unrealized_pnl_percent:.2f}%)"
        )


@dataclass
class SimulatedPortfolio:
    """
    Simulated portfolio for backtesting.

    Tracks cash, positions, and trade history during a backtest.

    Attributes:
        initial_capital: Starting capital
        cash: Current cash balance
        positions: Current stock positions
        trades: History of all trades
        commission_rate: Commission rate (as decimal, e.g., 0.001 for 0.1%)
        min_commission: Minimum commission per trade
    """

    initial_capital: float
    cash: float = field(init=False)
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    commission_rate: float = 0.0
    min_commission: float = 0.0

    # Portfolio history tracking
    _portfolio_history: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        """Initialize portfolio with starting cash."""
        self.cash = self.initial_capital
        logger.info(f"SimulatedPortfolio initialized with ${self.initial_capital:,.2f}")

    def execute_trade(
        self,
        ticker: str,
        signal: str,
        price: float,
        date: datetime,
        shares: Optional[float] = None,
        position_size: Optional[float] = None,
    ) -> Optional[Trade]:
        """
        Execute a trade based on signal.

        Args:
            ticker: Stock ticker symbol
            signal: Trading signal ('BUY', 'SELL', 'HOLD')
            price: Current price
            date: Trade date
            shares: Specific number of shares to trade (overrides position_size)
            position_size: Fraction of portfolio to allocate (0.0 to 1.0)

        Returns:
            Trade object if executed, None if signal was HOLD or trade failed

        Raises:
            DataValidationError: If position_size is invalid
        """
        signal = signal.upper()

        if signal == "HOLD":
            return None

        if signal == "BUY":
            return self._execute_buy(ticker, price, date, shares, position_size)
        elif signal == "SELL":
            return self._execute_sell(ticker, price, date, shares)
        else:
            logger.warning(f"Unknown signal: {signal}")
            return None

    def _execute_buy(
        self,
        ticker: str,
        price: float,
        date: datetime,
        shares: Optional[float] = None,
        position_size: Optional[float] = None,
    ) -> Optional[Trade]:
        """Execute a buy order."""
        # Determine number of shares to buy
        if shares is None:
            if position_size is None:
                raise DataValidationError(
                    "Either shares or position_size must be provided",
                    field="trade_params",
                    value="both None",
                    expected="shares or position_size",
                )

            if not 0 < position_size <= 1:
                raise DataValidationError(
                    "position_size must be between 0 and 1",
                    field="position_size",
                    value=position_size,
                    expected="0 < value <= 1",
                )

            # Calculate shares based on position size
            max_investment = self.cash * position_size
            shares = max_investment / price

        # Calculate commission
        commission = max(shares * price * self.commission_rate, self.min_commission)
        total_cost = (shares * price) + commission

        # Check if we have enough cash
        if total_cost > self.cash:
            logger.warning(
                f"Insufficient cash for {ticker}: need ${total_cost:,.2f}, "
                f"have ${self.cash:,.2f}"
            )
            return None

        # Execute trade
        trade = Trade(
            ticker=ticker,
            direction=TradeDirection.BUY,
            shares=shares,
            price=price,
            date=date,
            commission=commission,
        )

        # Update cash
        self.cash -= total_cost

        # Update or create position
        if ticker in self.positions:
            position = self.positions[ticker]
            # Update average price
            total_shares = position.shares + shares
            total_cost_basis = position.cost_basis + (shares * price)
            new_avg_price = total_cost_basis / total_shares

            position.shares = total_shares
            position.avg_price = new_avg_price
            position.update_price(price, date)
        else:
            self.positions[ticker] = Position(
                ticker=ticker,
                shares=shares,
                avg_price=price,
                current_price=price,
                last_update=date,
            )

        self.trades.append(trade)
        logger.info(f"Executed: {trade}")

        return trade

    def _execute_sell(
        self,
        ticker: str,
        price: float,
        date: datetime,
        shares: Optional[float] = None,
    ) -> Optional[Trade]:
        """Execute a sell order."""
        # Check if we have a position
        if ticker not in self.positions:
            logger.warning(f"No position to sell for {ticker}")
            return None

        position = self.positions[ticker]

        # Default to selling entire position
        if shares is None:
            shares = position.shares

        # Check if we have enough shares
        if shares > position.shares:
            logger.warning(
                f"Insufficient shares for {ticker}: trying to sell {shares:.2f}, "
                f"have {position.shares:.2f}"
            )
            return None

        # Calculate commission
        commission = max(shares * price * self.commission_rate, self.min_commission)
        proceeds = (shares * price) - commission

        # Execute trade
        trade = Trade(
            ticker=ticker,
            direction=TradeDirection.SELL,
            shares=shares,
            price=price,
            date=date,
            commission=commission,
        )

        # Update cash
        self.cash += proceeds

        # Update position
        position.shares -= shares
        position.update_price(price, date)

        # Remove position if fully closed
        if position.shares < 0.0001:  # Handle floating point precision
            del self.positions[ticker]

        self.trades.append(trade)
        logger.info(f"Executed: {trade}")

        return trade

    def get_portfolio_value(self, date: datetime) -> float:
        """
        Calculate total portfolio value (cash + positions).

        Args:
            date: Date for portfolio value calculation

        Returns:
            Total portfolio value
        """
        positions_value = sum(pos.market_value for pos in self.positions.values())
        total_value = self.cash + positions_value

        # Record portfolio value
        self._portfolio_history.append(
            {
                "date": date,
                "cash": self.cash,
                "positions_value": positions_value,
                "total_value": total_value,
            }
        )

        return total_value

    def get_holdings(self) -> Dict[str, Position]:
        """Get current holdings."""
        return self.positions.copy()

    def update_prices(self, prices: Dict[str, float], date: datetime) -> None:
        """
        Update current prices for all positions.

        Args:
            prices: Dictionary mapping ticker to current price
            date: Date of price update
        """
        for ticker, position in self.positions.items():
            if ticker in prices:
                position.update_price(prices[ticker], date)

    def get_portfolio_history(self) -> pd.DataFrame:
        """
        Get portfolio value history as DataFrame.

        Returns:
            DataFrame with columns: date, cash, positions_value, total_value
        """
        if not self._portfolio_history:
            return pd.DataFrame(
                columns=["date", "cash", "positions_value", "total_value"]
            )

        df = pd.DataFrame(self._portfolio_history)
        df.set_index("date", inplace=True)
        return df

    def get_trade_log(self) -> pd.DataFrame:
        """
        Get trade history as DataFrame.

        Returns:
            DataFrame with all trade details
        """
        if not self.trades:
            return pd.DataFrame(
                columns=[
                    "date",
                    "ticker",
                    "direction",
                    "shares",
                    "price",
                    "value",
                    "commission",
                    "total_cost",
                ]
            )

        trade_data = [
            {
                "date": t.date,
                "ticker": t.ticker,
                "direction": t.direction.value,
                "shares": t.shares,
                "price": t.price,
                "value": t.value,
                "commission": t.commission,
                "total_cost": t.total_cost,
                "notes": t.notes,
            }
            for t in self.trades
        ]

        df = pd.DataFrame(trade_data)
        df.set_index("date", inplace=True)
        return df

    def get_total_return(self) -> float:
        """Calculate total return as percentage."""
        current_value = self.cash + sum(
            pos.market_value for pos in self.positions.values()
        )
        return ((current_value - self.initial_capital) / self.initial_capital) * 100

    def get_total_commissions(self) -> float:
        """Calculate total commissions paid."""
        return sum(trade.commission for trade in self.trades)

    def __str__(self) -> str:
        """String representation of portfolio."""
        total_value = self.cash + sum(
            pos.market_value for pos in self.positions.values()
        )
        return (
            f"Portfolio Value: ${total_value:,.2f} "
            f"(Cash: ${self.cash:,.2f}, "
            f"Positions: {len(self.positions)}, "
            f"Trades: {len(self.trades)})"
        )
