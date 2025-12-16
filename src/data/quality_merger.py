"""
Data Quality Scoring and Merging Logic

Handles:
- Quality scoring for data sources
- Smart merging with quality-based field selection
- Coverage calculation
- Derived metric calculations
- Data integrity normalization
"""

import asyncio
import os
import re
import structlog
from collections import namedtuple
from typing import Dict, Any, Optional, List, Tuple, Set

from src.data.base_fetcher import (
    SOURCE_QUALITY,
    DataQuality,
    DEBT_EQUITY_PERCENTAGE_THRESHOLD,
    ROE_PERCENTAGE_THRESHOLD,
)

logger = structlog.get_logger(__name__)

# Optional Tavily import
try:
    from tavily import TavilyClient
    TAVILY_LIB_AVAILABLE = True
except ImportError:
    TAVILY_LIB_AVAILABLE = False
    logger.warning("tavily_python_not_available")

try:
    from src.ticker_utils import generate_strict_search_query
    TICKER_UTILS_AVAILABLE = True
except ImportError:
    TICKER_UTILS_AVAILABLE = False
    logger.warning("ticker_utils_not_available")


MergeResult = namedtuple('MergeResult', ['data', 'gaps_filled'])


class FinancialPatternExtractor:
    """Handles regex-based extraction of financial metrics from text."""

    def __init__(self):
        self.patterns = {
            'trailingPE': [
                re.compile(
                    r'(?:Trailing P/E|P/E \(TTM\)|P/E Ratio \(TTM\))(?:.*?)\s*[:=]?\s*(\d+[\.,]\d+)',
                    re.IGNORECASE
                ),
                re.compile(
                    r'(?:P/E|est|trading at|valuation).*?\s+(\d+[\.,]\d+)x',
                    re.IGNORECASE
                ),
                re.compile(
                    r'P/E\s+(?:of|is|around)\s+(\d+[\.,]\d+)',
                    re.IGNORECASE
                ),
                re.compile(
                    r'(?<!Forward\s)(?<!Fwd\s)(?:P/E|Price[- ]to[- ]Earnings)(?:.*?)(?:Ratio)?\s*[:=]?\s*(\d+[\.,]\d+)',
                    re.IGNORECASE
                ),
                re.compile(r'\btrades?\s+at\s+(\d+[\.,]\d+)x', re.IGNORECASE),
                re.compile(r'\bvalued\s+at\s+(\d+[\.,]\d+)x', re.IGNORECASE),
                re.compile(
                    r'\btrading\s+at\s+(\d+(?:[\.,]\d+)?)\s+times',
                    re.IGNORECASE
                ),
            ],
            'forwardPE': [
                re.compile(
                    r'(?:Forward P/E|Fwd P/E)(?:.*?)\s*[:=]?\s*(\d+[\.,]\d+)',
                    re.IGNORECASE
                ),
                re.compile(
                    r'(?:Forward P/E|Fwd P/E).*?(\d+[\.,]\d+)x',
                    re.IGNORECASE
                ),
                re.compile(r'est.*?P/E.*?(\d+[\.,]\d+)x', re.IGNORECASE)
            ],
            'priceToBook': [
                re.compile(
                    r'(?:P/B|Price[- ]to[- ]Book)(?:.*?)(?:Ratio)?\s*[:=]?\s*(\d+[\.,]\d+)',
                    re.IGNORECASE
                ),
                re.compile(r'PB\s*Ratio\s*[:=]?\s*(\d+[\.,]\d+)', re.IGNORECASE),
                re.compile(r'Price\s*/\s*Book\s*[:=]?\s*(\d+[\.,]\d+)', re.IGNORECASE),
                re.compile(r'trading at\s+(\d+[\.,]\d+)x\s+book', re.IGNORECASE)
            ],
            'returnOnEquity': [
                re.compile(r'(?:ROE|Return on Equity).*?(\d+[\.,]\d+)%?', re.IGNORECASE)
            ],
            'marketCap': [
                re.compile(
                    r'(?:Market Cap|Valuation).*?(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d+)?)\s*([TBM])',
                    re.IGNORECASE
                )
            ],
            'enterpriseToEbitda': [
                re.compile(
                    r'(?:EV/EBITDA|Enterprise Value/EBITDA)(?:.*?)\s*[:=]?\s*(\d+[\.,]\d+)',
                    re.IGNORECASE
                ),
                re.compile(r'EV/EBITDA.*?(\d+[\.,]\d+)x', re.IGNORECASE)
            ],
            'numberOfAnalystOpinions': [
                re.compile(r'(\d+)\s+analyst(?:s)?\s+cover', re.IGNORECASE),
                re.compile(r'covered\s+by\s+(\d+)\s+analyst', re.IGNORECASE),
                re.compile(r'(\d+)\s+analyst(?:s)?\s+rating', re.IGNORECASE),
                re.compile(r'analyst\s+coverage:\s*(\d+)', re.IGNORECASE),
                re.compile(r'based\s+on\s+(\d+)\s+analyst', re.IGNORECASE),
                re.compile(r'consensus.*?(\d+)\s+analyst', re.IGNORECASE),
                re.compile(r'(\d+)\s+wall\s+street\s+analyst', re.IGNORECASE)
            ],
            'us_revenue_pct': [
                re.compile(
                    r'US\s+revenue\s+.*?\s+(\d+(?:\.\d+)?)%',
                    re.IGNORECASE
                ),
                re.compile(
                    r'North\s+America\s+revenue\s+.*?\s+(\d+(?:\.\d+)?)%',
                    re.IGNORECASE
                ),
                re.compile(
                    r'revenue\s+from\s+.*?Americas.*?\s+(\d+(?:\.\d+)?)%',
                    re.IGNORECASE
                )
            ]
        }

        self.multipliers = {'T': 1e12, 'B': 1e9, 'M': 1e6}

    def _normalize_number(self, val_str: str) -> float:
        """Normalize number string handling international formats."""
        try:
            val_str = val_str.strip()
            val_str = re.sub(r'[xX%]$', '', val_str).strip()

            # Robust International Format Handling
            if ',' in val_str and '.' in val_str:
                if val_str.rfind(',') < val_str.rfind('.'):
                    clean_str = val_str.replace(',', '')  # US: 1,234.56
                else:
                    clean_str = val_str.replace('.', '').replace(',', '.')  # EU: 1.234,56
            elif ',' in val_str:
                # Ambiguous: 1,234 vs 12,34. Assume comma as decimal if not xxx,xxx
                if re.match(r'^\d{1,3},\d{3}$', val_str):
                    clean_str = val_str.replace(',', '')
                else:
                    clean_str = val_str.replace(',', '.')
            else:
                clean_str = val_str

            return float(clean_str)
        except ValueError:
            return 0.0

    def extract_from_text(
        self,
        content: str,
        skip_fields: Set[str] = None
    ) -> Dict[str, Any]:
        """Extract financial metrics from text using regex patterns."""
        skip_fields = skip_fields or set()
        extracted = {}

        for field, pattern_list in self.patterns.items():
            if field != 'forwardPE' and field in skip_fields:
                continue

            for pattern in pattern_list:
                match = pattern.search(content)
                if match:
                    try:
                        val_str = match.group(1)
                        val = self._normalize_number(val_str)

                        if field == 'returnOnEquity' and val > ROE_PERCENTAGE_THRESHOLD:
                            val = val / 100.0
                        elif field == 'marketCap':
                            suffix = match.group(2).upper()
                            multiplier = self.multipliers.get(suffix, 1)
                            val = val * multiplier
                        elif field == 'numberOfAnalystOpinions':
                            val = int(val)
                            if val < 0 or val > 200:
                                continue  # Sanity check

                        extracted[field] = val
                        extracted[f'_{field}_source'] = 'web_search_extraction'
                        break
                    except (ValueError, IndexError):
                        continue

        # Proxy fill
        if ('trailingPE' not in skip_fields and
                'trailingPE' not in extracted and
                'forwardPE' in extracted):
            extracted['trailingPE'] = extracted['forwardPE']
            extracted['_trailingPE_source'] = 'proxy_from_forward_pe'

        return extracted


class QualityMerger:
    """
    Handles intelligent merging of data from multiple sources with quality scoring.
    """

    IMPORTANT_FIELDS = [
        'marketCap', 'trailingPE', 'priceToBook', 'returnOnEquity',
        'revenueGrowth', 'profitMargins', 'operatingMargins', 'grossMargins',
        'debtToEquity', 'currentRatio', 'freeCashflow', 'operatingCashflow',
        'numberOfAnalystOpinions', 'pegRatio', 'forwardPE'
    ]

    REQUIRED_BASICS = ['symbol', 'currentPrice', 'currency']

    CRITICAL_GAPS = [
        'trailingPE', 'forwardPE', 'priceToBook', 'pegRatio',
        'returnOnEquity', 'returnOnAssets', 'debtToEquity',
        'currentRatio', 'operatingMargins', 'grossMargins',
        'profitMargins', 'revenueGrowth', 'earningsGrowth',
        'operatingCashflow', 'freeCashflow', 'numberOfAnalystOpinions'
    ]

    # Fields that should not be filled from web search (too risky)
    DANGEROUS_FIELDS = [
        'trailingPE', 'forwardPE', 'pegRatio', 'currentPrice', 'marketCap'
    ]

    # Search terms for web search gap filling
    FIELD_SEARCH_TERMS = {
        'trailingPE': "trailing P/E ratio price earnings",
        'forwardPE': "forward P/E ratio estimate",
        'priceToBook': "price to book ratio P/B",
        'returnOnEquity': "ROE return on equity",
        'debtToEquity': "debt to equity ratio leverage",
        'numberOfAnalystOpinions': "analyst coverage count",
        'revenueGrowth': "revenue growth year over year",
    }

    def __init__(self):
        self.pattern_extractor = FinancialPatternExtractor()
        api_key = os.environ.get("TAVILY_API_KEY")
        self.tavily_client = (
            TavilyClient(api_key=api_key)
            if TAVILY_LIB_AVAILABLE and api_key
            else None
        )

    def smart_merge_with_quality(
        self,
        source_results: Dict[str, Optional[Dict]],
        symbol: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Intelligent merge with quality scoring.

        Processes sources in order of quality and merges fields
        based on source reliability.

        Args:
            source_results: Dictionary mapping source names to their data
            symbol: The ticker symbol being processed

        Returns:
            Tuple of (merged_data, metadata)
        """
        merged = {}
        field_sources = {}
        field_quality = {}
        sources_used = set()
        gaps_filled = 0

        # Process in order (lowest to highest priority for base processing)
        source_order = ['yahooquery', 'fmp', 'alpha_vantage', 'eodhd', 'yfinance']

        for source_name in source_order:
            source_data = source_results.get(source_name)
            if not source_data:
                continue

            sources_used.add(source_name)

            for key, value in source_data.items():
                if value is None:
                    continue

                if key.startswith('_') and key.endswith('_source'):
                    continue

                # Determine base quality for this source
                if source_name in SOURCE_QUALITY:
                    quality = SOURCE_QUALITY[source_name]
                else:
                    quality = SOURCE_QUALITY.get(f"{source_name}_info", 5)

                # Check for field-specific override
                source_tag_key = f"_{key}_source"
                if source_tag_key in source_data:
                    tag = source_data[source_tag_key]
                    if tag in SOURCE_QUALITY:
                        quality = SOURCE_QUALITY[tag]

                should_use = False

                if key not in merged:
                    should_use = True
                elif merged[key] is None and value is not None:
                    should_use = True
                    gaps_filled += 1
                elif key in field_quality:
                    if quality > field_quality[key]:
                        should_use = True
                        logger.debug(
                            "replacing_with_higher_quality",
                            symbol=symbol,
                            field=key,
                            old_source=field_sources.get(key),
                            new_source=source_name
                        )

                if should_use:
                    merged[key] = value
                    field_sources[key] = source_name
                    field_quality[key] = quality

        metadata = {
            'sources_used': list(sources_used),
            'composite_source': f"composite_{'+'.join(sorted(sources_used))}",
            'gaps_filled': gaps_filled,
            'field_sources': field_sources,
            'field_quality': field_quality
        }

        logger.info(
            "smart_merge_complete",
            symbol=symbol,
            total_fields=len(merged),
            sources=list(sources_used),
            gaps_filled=gaps_filled
        )

        return merged, metadata

    def calculate_coverage(self, data: Dict[str, Any]) -> float:
        """Calculate percentage of IMPORTANT_FIELDS present."""
        if not data:
            return 0.0
        present = sum(
            1 for field in self.IMPORTANT_FIELDS
            if data.get(field) is not None
        )
        return present / len(self.IMPORTANT_FIELDS) if self.IMPORTANT_FIELDS else 0.0

    def identify_critical_gaps(self, data: Dict[str, Any]) -> List[str]:
        """Identify which critical fields are missing."""
        return [f for f in self.CRITICAL_GAPS if f not in data or data[f] is None]

    async def fetch_tavily_gaps(
        self,
        symbol: str,
        missing_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Tavily gap-filling for missing fields.

        Args:
            symbol: Ticker symbol
            missing_fields: List of fields to try to fill

        Returns:
            Dictionary of extracted values
        """
        safe_missing_fields = [
            f for f in missing_fields
            if f not in self.DANGEROUS_FIELDS
        ]

        if 'us_revenue_pct' in missing_fields or 'geographic_revenue' in missing_fields:
            safe_missing_fields.append('us_revenue_pct')

        if not self.tavily_client or not safe_missing_fields:
            return {}

        # Get company name for better search
        company_name = self._get_company_name(symbol)

        fields_to_search = safe_missing_fields[:5]
        search_results = {}

        for field in fields_to_search:
            query = self._build_search_query(symbol, company_name, field)

            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.tavily_client.search,
                        query,
                        max_results=3
                    ),
                    timeout=5
                )
                if result and 'results' in result:
                    combined = "\n".join([
                        i.get('content', '') for i in result['results']
                    ])
                    search_results[field] = combined
            except asyncio.TimeoutError:
                logger.debug("tavily_search_timeout", symbol=symbol, field=field)
            except asyncio.CancelledError:
                logger.debug("tavily_search_cancelled", symbol=symbol, field=field)
            except (KeyError, TypeError) as e:
                logger.debug(
                    "tavily_search_result_parse_error",
                    symbol=symbol,
                    field=field,
                    error_type=type(e).__name__,
                    error=str(e)
                )
            except (ConnectionError, OSError) as e:
                logger.debug(
                    "tavily_search_network_error",
                    symbol=symbol,
                    field=field,
                    error_type=type(e).__name__,
                    error=str(e)
                )
            except Exception as e:
                logger.debug(
                    "tavily_search_failed",
                    symbol=symbol,
                    field=field,
                    error_type=type(e).__name__,
                    error=str(e)
                )

        if not search_results:
            return {}

        all_text = "\n\n".join(search_results.values())
        return self.pattern_extractor.extract_from_text(all_text, skip_fields=set())

    def _get_company_name(self, symbol: str) -> str:
        """Get company name for search queries."""
        try:
            import yfinance as yf
            ticker_obj = yf.Ticker(symbol)
            return (
                ticker_obj.info.get('longName') or
                ticker_obj.info.get('shortName') or
                symbol
            )
        except Exception as e:
            logger.debug(
                "company_name_lookup_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
            return symbol

    def _build_search_query(
        self,
        symbol: str,
        company_name: str,
        field: str
    ) -> str:
        """Build search query for a specific field."""
        if field == 'us_revenue_pct':
            return (
                f'"{company_name}" annual report revenue by geography '
                f'North America United States'
            )

        term = self.FIELD_SEARCH_TERMS.get(field, field)

        if TICKER_UTILS_AVAILABLE:
            return generate_strict_search_query(symbol, company_name, term)

        return f'"{company_name}" {symbol} {term}'

    def merge_gap_fill_data(
        self,
        merged: Dict[str, Any],
        gap_fill_data: Dict[str, Any],
        merge_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge Tavily gap-fill data into merged results."""
        tavily_quality = SOURCE_QUALITY['tavily_extraction']
        added = 0

        for key, value in gap_fill_data.items():
            if value is None:
                continue

            should_use = False

            if key not in merged:
                should_use = True
            elif merged[key] is None:
                should_use = True
            elif (key in merge_metadata['field_quality'] and
                  tavily_quality > merge_metadata['field_quality'][key]):
                should_use = True

            if should_use:
                merged[key] = value
                merge_metadata['field_sources'][key] = 'tavily'
                merge_metadata['field_quality'][key] = tavily_quality
                added += 1

        merge_metadata['gaps_filled'] += added
        return merged

    def calculate_derived_metrics(
        self,
        data: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Calculate derived metrics from available data."""
        calculated = {}

        try:
            # ROE from ROA and D/E
            if data.get('returnOnEquity') is None:
                roa = data.get('returnOnAssets')
                de = data.get('debtToEquity')
                if roa is not None and de is not None:
                    calculated['returnOnEquity'] = roa * (1 + de)
                    calculated['_returnOnEquity_source'] = 'calculated_from_roa_de'

            # PEG from P/E and earnings growth
            if data.get('pegRatio') is None:
                pe = data.get('trailingPE')
                growth = data.get('earningsGrowth')
                if pe and growth and growth > 0:
                    calculated['pegRatio'] = pe / (growth * 100)
                    calculated['_pegRatio_source'] = 'calculated_from_pe_growth'

            # Market cap from price and shares
            if data.get('marketCap') is None:
                price = data.get('currentPrice') or data.get('regularMarketPrice')
                shares = data.get('sharesOutstanding')
                if price and shares:
                    calculated['marketCap'] = price * shares
                    calculated['_marketCap_source'] = 'calculated_from_price_shares'

        except (TypeError, ValueError) as e:
            logger.debug(
                "derived_metrics_calculation_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )
        except ZeroDivisionError:
            logger.debug("derived_metrics_division_by_zero", symbol=symbol)
        except Exception as e:
            logger.warning(
                "derived_metrics_unexpected_error",
                symbol=symbol,
                error_type=type(e).__name__,
                error=str(e)
            )

        return calculated

    def merge_data(
        self,
        primary: Dict[str, Any],
        *fallbacks: Dict[str, Any]
    ) -> MergeResult:
        """Simple dictionary merge for derived data."""
        merged = primary.copy() if primary else {}
        gaps = 0

        for fb in fallbacks:
            if not fb:
                continue
            for k, v in fb.items():
                if k in merged and merged[k] is not None:
                    continue
                if v is not None:
                    merged[k] = v
                    if not k.startswith('_'):
                        gaps += 1

        return MergeResult(merged, gaps)

    def validate_basics(
        self,
        data: Dict[str, Any],
        symbol: str,
        sources_used: List[str] = None
    ) -> DataQuality:
        """Validate that basic required fields are present."""
        quality = DataQuality()
        quality.sources_used = sources_used or []

        missing = []
        for field in self.REQUIRED_BASICS:
            if field == 'currentPrice':
                if not any(
                    k in data
                    for k in ['currentPrice', 'regularMarketPrice', 'previousClose']
                ):
                    missing.append('price')
            elif data.get(field) is None:
                missing.append(field)

        quality.basics_missing = missing
        quality.basics_ok = len(missing) == 0

        present = sum(
            1 for field in self.IMPORTANT_FIELDS
            if data.get(field) is not None
        )
        quality.coverage_pct = (present / len(self.IMPORTANT_FIELDS)) * 100

        return quality


class DataNormalizer:
    """Handles data integrity normalization and fixes."""

    def __init__(self, fx_rate_fetcher=None):
        self.fx_rate_fetcher = fx_rate_fetcher

    def normalize_data_integrity(
        self,
        info: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Apply all normalization fixes to data."""
        info = self._fix_currency_mismatch(info, symbol)
        info = self._fix_debt_equity_scaling(info, symbol)
        info = self._normalize_pe_ratio(info, symbol)
        return info

    def _fix_currency_mismatch(
        self,
        info: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Fix currency mismatch between trading and financial currencies."""
        trading_curr = info.get('currency', 'USD').upper()
        financial_curr = info.get('financialCurrency', trading_curr).upper()
        price = info.get('currentPrice')
        book = info.get('bookValue')

        if not (book and price):
            return info

        if trading_curr != financial_curr:
            fx = self._get_fx_rate(financial_curr, trading_curr)
            if abs(fx - 1.0) > 0.1:
                info['bookValue'] = book * fx
                info['priceToBook'] = price / info['bookValue']

        return info

    def _fix_debt_equity_scaling(
        self,
        info: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Fix debt/equity ratio if reported as percentage."""
        de = info.get('debtToEquity')
        if de is not None and de > DEBT_EQUITY_PERCENTAGE_THRESHOLD:
            info['debtToEquity'] = de / 100.0
        return info

    def _normalize_pe_ratio(
        self,
        info: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Normalize P/E ratio if trailing is unreasonably higher than forward."""
        trailing = info.get('trailingPE')
        forward = info.get('forwardPE')

        if trailing and forward and trailing > 0 and forward > 0:
            if trailing > (forward * 1.4):
                info['trailingPE'] = forward
                info['_trailingPE_source'] = 'normalized_forward_proxy'

        return info

    def _get_fx_rate(self, from_curr: str, to_curr: str) -> float:
        """Get FX rate using the provided fetcher or return 1.0."""
        if self.fx_rate_fetcher:
            return self.fx_rate_fetcher(from_curr, to_curr)
        return 1.0
