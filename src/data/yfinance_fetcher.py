"""
YFinance-specific Data Fetcher

Handles all yfinance and yahooquery data fetching:
- Enhanced yfinance fetching with statement extraction
- Financial statement calculations
- Yahooquery fallback fetching
"""

import asyncio
import yfinance as yf
import pandas as pd
import structlog
from typing import Dict, Any, Optional, List

from src.data.base_fetcher import (
    BaseFetcher,
    MIN_INFO_FIELDS,
    FXRateCache,
    FX_CACHE_TTL_SECONDS,
)

logger = structlog.get_logger(__name__)

# Optional yahooquery import
try:
    from yahooquery import Ticker as YQTicker
    YAHOOQUERY_AVAILABLE = True
except ImportError:
    YAHOOQUERY_AVAILABLE = False
    logger.warning("yahooquery_not_available")


class YFinanceFetcher(BaseFetcher):
    """
    YFinance data fetcher with enhanced statement extraction.

    Fetches data from yfinance including:
    - Basic info and price data
    - Financial statements (income, balance sheet, cash flow)
    - Calculated metrics from statements
    """

    def __init__(self, timeout: int = 15):
        super().__init__(timeout)
        self.fx_cache = FXRateCache(FX_CACHE_TTL_SECONDS)

    async def fetch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch yfinance data including statement calculations.

        Args:
            symbol: Ticker symbol to fetch

        Returns:
            Dictionary with merged info and statement data, or None
        """
        try:
            ticker = yf.Ticker(symbol)
            info = self._get_ticker_info(ticker, symbol)
            has_price = self._check_price_available(info, ticker)

            if not has_price:
                logger.warning("yfinance_no_price", symbol=symbol)
                info = info or {}

            # Always extract from statements
            statement_data = self._extract_from_financial_statements(ticker, symbol)
            info = self._merge_statement_data(info, statement_data)

            if not info or (not has_price and len(info) < 5):
                return None

            if 'symbol' not in info:
                info['symbol'] = symbol

            return info

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "yfinance_network_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except (ValueError, TypeError) as e:
            logger.warning(
                "yfinance_data_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.error(
                "yfinance_enhanced_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate that data contains minimum required fields."""
        if not data:
            return False

        price_fields = ['currentPrice', 'regularMarketPrice', 'previousClose']
        has_price = any(data.get(f) is not None for f in price_fields)

        return has_price and len(data) >= MIN_INFO_FIELDS

    def _get_ticker_info(self, ticker: yf.Ticker, symbol: str) -> Dict[str, Any]:
        """Safely get ticker info."""
        info = {}
        try:
            info = ticker.info
        except (KeyError, ValueError) as e:
            logger.debug(
                "yfinance_info_access_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            info = {}
        except AttributeError as e:
            logger.debug(
                "yfinance_info_attribute_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            info = {}
        return info

    def _check_price_available(
        self,
        info: Dict[str, Any],
        ticker: yf.Ticker
    ) -> bool:
        """Check if price data is available."""
        price_fields = ['currentPrice', 'regularMarketPrice', 'previousClose']
        has_price = False

        if info:
            for field in price_fields:
                if field in info and info[field] is not None:
                    has_price = True
                    break

        if not has_price and hasattr(ticker, 'fast_info'):
            try:
                fast_price = ticker.fast_info.get('lastPrice')
                if fast_price:
                    info['currentPrice'] = fast_price
                    has_price = True
            except (AttributeError, KeyError) as e:
                logger.debug(
                    "yfinance_fast_info_access_error",
                    symbol=info.get('symbol', 'unknown'),
                    error_type=type(e).__name__,
                    error=str(e)
                )
            except TypeError as e:
                logger.debug(
                    "yfinance_fast_info_type_error",
                    symbol=info.get('symbol', 'unknown'),
                    error_type=type(e).__name__,
                    error=str(e)
                )

        return has_price

    def _merge_statement_data(
        self,
        info: Dict[str, Any],
        statement_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge statement-extracted data into info."""
        for key, value in statement_data.items():
            if key.startswith('_'):
                info[key] = value
            elif key not in info or info.get(key) is None:
                if value is not None:
                    info[key] = value
        return info

    def _extract_from_financial_statements(
        self,
        ticker: yf.Ticker,
        symbol: str
    ) -> Dict[str, Any]:
        """
        Extract metrics from yfinance financial statements.

        Extracts:
        - Revenue growth from income statement
        - Margins (gross, operating, profit)
        - Cash flow metrics
        - Balance sheet ratios
        """
        extracted = {}

        try:
            financials = ticker.financials
            cashflow = ticker.cashflow
            balance_sheet = ticker.balance_sheet

            if financials.empty and cashflow.empty and balance_sheet.empty:
                return extracted

            # Income statement extractions
            extracted.update(
                self._extract_income_statement_metrics(financials, symbol)
            )

            # Cash flow extractions
            extracted.update(
                self._extract_cashflow_metrics(cashflow, symbol)
            )

            # Balance sheet extractions
            extracted.update(
                self._extract_balance_sheet_metrics(balance_sheet, symbol)
            )

        except AttributeError as e:
            logger.debug(
                "statement_extraction_attribute_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except (KeyError, IndexError) as e:
            logger.debug(
                "statement_extraction_data_access_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except Exception as e:
            logger.warning(
                "statement_extraction_unexpected_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )

        return extracted

    def _extract_income_statement_metrics(
        self,
        financials: pd.DataFrame,
        symbol: str
    ) -> Dict[str, Any]:
        """Extract metrics from income statement."""
        extracted = {}

        if financials.empty:
            return extracted

        # Revenue Growth
        if 'Total Revenue' in financials.index and len(financials.columns) >= 2:
            try:
                revenue_series = financials.loc['Total Revenue']
                current = float(revenue_series.iloc[0])
                previous = float(revenue_series.iloc[1])

                if previous and previous != 0:
                    growth = (current - previous) / previous
                    if -0.5 < growth < 5.0:
                        extracted['revenueGrowth'] = growth
                        extracted['_revenueGrowth_source'] = 'calculated_from_statements'
            except (KeyError, IndexError) as e:
                logger.debug(
                    "revenue_growth_extraction_failed",
                    symbol=symbol,
                    error_type=type(e).__name__,
                    error=str(e)
                )
            except (ValueError, TypeError) as e:
                logger.debug(
                    "revenue_growth_calculation_failed",
                    symbol=symbol,
                    error_type=type(e).__name__,
                    error=str(e)
                )
            except ZeroDivisionError:
                logger.debug("revenue_growth_division_by_zero", symbol=symbol)

        # Margins
        try:
            if 'Gross Profit' in financials.index and 'Total Revenue' in financials.index:
                gross_profit = float(financials.loc['Gross Profit'].iloc[0])
                revenue = float(financials.loc['Total Revenue'].iloc[0])
                if revenue:
                    extracted['grossMargins'] = gross_profit / revenue
                    extracted['_grossMargins_source'] = 'calculated_from_statements'

            if 'Operating Income' in financials.index and 'Total Revenue' in financials.index:
                op_income = float(financials.loc['Operating Income'].iloc[0])
                revenue = float(financials.loc['Total Revenue'].iloc[0])
                if revenue:
                    extracted['operatingMargins'] = op_income / revenue
                    extracted['_operatingMargins_source'] = 'calculated_from_statements'

            if 'Net Income' in financials.index and 'Total Revenue' in financials.index:
                net_income = float(financials.loc['Net Income'].iloc[0])
                revenue = float(financials.loc['Total Revenue'].iloc[0])
                if revenue:
                    extracted['profitMargins'] = net_income / revenue
                    extracted['_profitMargins_source'] = 'calculated_from_statements'
        except (KeyError, IndexError) as e:
            logger.debug(
                "margins_extraction_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except (ValueError, TypeError) as e:
            logger.debug(
                "margins_calculation_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except ZeroDivisionError:
            logger.debug("margins_division_by_zero", symbol=symbol)

        return extracted

    def _extract_cashflow_metrics(
        self,
        cashflow: pd.DataFrame,
        symbol: str
    ) -> Dict[str, Any]:
        """Extract metrics from cash flow statement."""
        extracted = {}

        if cashflow.empty:
            return extracted

        # Operating Cash Flow
        if 'Operating Cash Flow' in cashflow.index:
            try:
                ocf = float(cashflow.loc['Operating Cash Flow'].iloc[0])
                extracted['operatingCashflow'] = ocf
                extracted['_operatingCashflow_source'] = 'extracted_from_statements'
            except (KeyError, IndexError) as e:
                logger.debug(
                    "operating_cashflow_extraction_failed",
                    symbol=symbol,
                    error_type=type(e).__name__,
                    error=str(e)
                )
            except (ValueError, TypeError) as e:
                logger.debug(
                    "operating_cashflow_conversion_failed",
                    symbol=symbol,
                    error_type=type(e).__name__,
                    error=str(e)
                )

        # Free Cash Flow
        try:
            if ('Operating Cash Flow' in cashflow.index and
                    'Capital Expenditure' in cashflow.index):
                ocf = float(cashflow.loc['Operating Cash Flow'].iloc[0])
                capex = float(cashflow.loc['Capital Expenditure'].iloc[0])
                fcf = ocf + capex  # Capex is usually negative
                extracted['freeCashflow'] = fcf
                extracted['_freeCashflow_source'] = 'calculated_from_statements'
        except (KeyError, IndexError) as e:
            logger.debug(
                "free_cashflow_extraction_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except (ValueError, TypeError) as e:
            logger.debug(
                "free_cashflow_calculation_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )

        return extracted

    def _extract_balance_sheet_metrics(
        self,
        balance_sheet: pd.DataFrame,
        symbol: str
    ) -> Dict[str, Any]:
        """Extract metrics from balance sheet."""
        extracted = {}

        if balance_sheet.empty:
            return extracted

        # Current Ratio
        try:
            if ('Current Assets' in balance_sheet.index and
                    'Current Liabilities' in balance_sheet.index):
                current_assets = float(balance_sheet.loc['Current Assets'].iloc[0])
                current_liabilities = float(
                    balance_sheet.loc['Current Liabilities'].iloc[0]
                )
                if current_liabilities:
                    extracted['currentRatio'] = current_assets / current_liabilities
                    extracted['_currentRatio_source'] = 'calculated_from_statements'
        except (KeyError, IndexError) as e:
            logger.debug(
                "current_ratio_extraction_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except (ValueError, TypeError) as e:
            logger.debug(
                "current_ratio_calculation_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except ZeroDivisionError:
            logger.debug("current_ratio_division_by_zero", symbol=symbol)

        # Debt to Equity
        try:
            debt = None
            equity = None

            if 'Total Debt' in balance_sheet.index:
                debt = float(balance_sheet.loc['Total Debt'].iloc[0])
            elif 'Long Term Debt' in balance_sheet.index:
                long_term = float(balance_sheet.loc['Long Term Debt'].iloc[0])
                short_term = 0
                if 'Current Debt' in balance_sheet.index:
                    short_term = float(balance_sheet.loc['Current Debt'].iloc[0])
                debt = long_term + short_term

            if 'Stockholders Equity' in balance_sheet.index:
                equity = float(balance_sheet.loc['Stockholders Equity'].iloc[0])
            elif 'Total Stockholder Equity' in balance_sheet.index:
                equity = float(
                    balance_sheet.loc['Total Stockholder Equity'].iloc[0]
                )

            if debt is not None and equity is not None and equity != 0:
                extracted['debtToEquity'] = debt / equity
                extracted['_debtToEquity_source'] = 'calculated_from_statements'
        except (KeyError, IndexError) as e:
            logger.debug(
                "debt_equity_extraction_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except (ValueError, TypeError) as e:
            logger.debug(
                "debt_equity_calculation_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except ZeroDivisionError:
            logger.debug("debt_equity_division_by_zero", symbol=symbol)

        return extracted

    def get_currency_rate(self, from_curr: str, to_curr: str) -> float:
        """Get FX rate with caching."""
        if not from_curr or not to_curr or from_curr == to_curr:
            return 1.0

        from_curr = from_curr.upper()
        to_curr = to_curr.upper()

        # Check cache first
        cached = self.fx_cache.get(from_curr, to_curr)
        if cached is not None:
            return cached

        try:
            pair_symbol = f"{from_curr}{to_curr}=X"
            ticker = yf.Ticker(pair_symbol)
            hist = ticker.history(period="1d")

            if not hist.empty:
                rate = float(hist['Close'].iloc[-1])
                self.fx_cache.set(from_curr, to_curr, rate)
                return rate
        except (KeyError, IndexError) as e:
            logger.debug(
                "fx_rate_data_access_error",
                pair=f"{from_curr}/{to_curr}",
                error=str(e)
            )
        except ValueError as e:
            logger.debug(
                "fx_rate_conversion_error",
                pair=f"{from_curr}/{to_curr}",
                error=str(e)
            )
        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "fx_rate_network_error",
                pair=f"{from_curr}/{to_curr}",
                error=str(e)
            )
        except Exception as e:
            logger.warning(
                "fx_rate_fetch_failed",
                pair=f"{from_curr}/{to_curr}",
                error_type=type(e).__name__,
                error=str(e)
            )

        return 1.0

    async def get_historical_prices(
        self,
        ticker: str,
        period: str = "1y"
    ) -> pd.DataFrame:
        """Fetch historical price data."""
        try:
            stock = yf.Ticker(ticker)
            hist = await asyncio.to_thread(stock.history, period=period)
            return hist
        except asyncio.CancelledError:
            logger.warning("history_fetch_cancelled", ticker=ticker)
            raise
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(
                "history_fetch_network_error",
                ticker=ticker,
                error_type=type(e).__name__,
                error=str(e)
            )
            return pd.DataFrame()
        except (ValueError, KeyError) as e:
            logger.warning(
                "history_fetch_data_error",
                ticker=ticker,
                error_type=type(e).__name__,
                error=str(e)
            )
            return pd.DataFrame()
        except Exception as e:
            logger.error(
                "history_fetch_failed",
                ticker=ticker,
                error_type=type(e).__name__,
                error=str(e)
            )
            return pd.DataFrame()


class YahooQueryFetcher(BaseFetcher):
    """
    YahooQuery fallback fetcher.

    Uses yahooquery library as a backup data source.
    """

    def __init__(self, timeout: int = 15):
        super().__init__(timeout)
        self._available = YAHOOQUERY_AVAILABLE

    async def fetch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data using yahooquery."""
        if not self._available:
            return None

        # Run synchronous yahooquery in thread pool
        return await asyncio.to_thread(self._fetch_sync, symbol)

    def _fetch_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Synchronous yahooquery fetch."""
        if not YAHOOQUERY_AVAILABLE:
            return None

        try:
            yq = YQTicker(symbol)
            combined = {}
            modules = [
                yq.summary_profile,
                yq.summary_detail,
                yq.key_stats,
                yq.financial_data,
                yq.price
            ]

            for module in modules:
                if isinstance(module, dict) and symbol in module:
                    data = module[symbol]
                    if isinstance(data, dict):
                        combined.update(data)

            if not combined or len(combined) < MIN_INFO_FIELDS:
                return None

            if 'currentPrice' not in combined and 'regularMarketPrice' in combined:
                combined['currentPrice'] = combined['regularMarketPrice']

            return combined

        except (KeyError, AttributeError) as e:
            logger.debug(
                "yahooquery_data_access_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "yahooquery_network_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.warning(
                "yahooquery_fallback_failed",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return None

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate yahooquery data."""
        if not data:
            return False
        return len(data) >= MIN_INFO_FIELDS

    def is_available(self) -> bool:
        """Check if yahooquery is available."""
        return self._available
