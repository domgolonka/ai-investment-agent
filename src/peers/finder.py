"""
PeerFinder - Auto-detect and retrieve industry peers for stock analysis.

This module provides intelligent peer detection using yfinance sector/industry data
with caching to minimize API calls and support for international tickers.
"""

import yfinance as yf
import structlog
import asyncio
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from src.exceptions import (
    DataFetchError,
    TickerNotFoundError,
    TickerValidationError,
)

logger = structlog.get_logger(__name__)


@dataclass
class SectorInfo:
    """Sector and industry information for a ticker."""

    ticker: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def is_valid(self) -> bool:
        """Check if sector info contains minimum required data."""
        return bool(self.sector and self.industry)

    def is_stale(self, ttl_hours: int = 24) -> bool:
        """Check if cached data is stale."""
        age = datetime.utcnow() - self.last_updated
        return age > timedelta(hours=ttl_hours)


@dataclass
class PeerGroup:
    """A group of peer companies with metadata."""

    focus_ticker: str
    peers: List[str]
    sector: str
    industry: str
    total_candidates: int
    filters_applied: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def get_all_tickers(self) -> List[str]:
        """Get all tickers including the focus ticker."""
        return [self.focus_ticker] + self.peers


class PeerFinder:
    """
    Find industry peers for stock analysis using yfinance sector/industry data.

    Features:
    - Auto-detect peers based on sector and industry classification
    - Cache sector/industry data to minimize API calls
    - Support for international tickers
    - Market cap filtering to ensure comparable companies
    - Configurable peer group size

    Example:
        finder = PeerFinder()
        peers = await finder.find_peers("AAPL")
        # Returns: ["MSFT", "GOOGL", "META", ...]

        sector_info = await finder.get_sector_info("TSLA")
        # Returns: SectorInfo(sector="Consumer Cyclical", industry="Auto Manufacturers")
    """

    def __init__(
        self,
        cache_ttl_hours: int = 24,
        max_peers: int = 10,
        min_market_cap_ratio: float = 0.1,
        max_market_cap_ratio: float = 10.0,
    ):
        """
        Initialize PeerFinder.

        Args:
            cache_ttl_hours: Hours before cached sector info expires
            max_peers: Maximum number of peers to return
            min_market_cap_ratio: Minimum market cap as ratio of focus ticker
            max_market_cap_ratio: Maximum market cap as ratio of focus ticker
        """
        self._sector_cache: Dict[str, SectorInfo] = {}
        self._industry_tickers: Dict[str, Set[str]] = defaultdict(set)
        self._cache_ttl_hours = cache_ttl_hours
        self._max_peers = max_peers
        self._min_market_cap_ratio = min_market_cap_ratio
        self._max_market_cap_ratio = max_market_cap_ratio
        logger.info(
            "peer_finder_initialized",
            cache_ttl_hours=cache_ttl_hours,
            max_peers=max_peers,
        )

    async def find_peers(
        self,
        ticker: str,
        max_peers: Optional[int] = None,
        same_country: bool = False,
        min_market_cap: Optional[float] = None,
    ) -> List[str]:
        """
        Find industry peers for a given ticker.

        Args:
            ticker: The ticker symbol to find peers for
            max_peers: Override default max peers
            same_country: Only include peers from same country
            min_market_cap: Minimum market cap threshold (USD)

        Returns:
            List of peer ticker symbols

        Raises:
            TickerNotFoundError: If ticker cannot be found
            DataFetchError: If peer data cannot be fetched
        """
        ticker = ticker.upper().strip()
        max_peers = max_peers or self._max_peers

        logger.info("finding_peers", ticker=ticker, max_peers=max_peers)

        # Get sector info for focus ticker
        sector_info = await self.get_sector_info(ticker)

        if not sector_info.is_valid():
            raise DataFetchError(
                "Cannot find peers: missing sector/industry data",
                ticker=ticker,
                details={"sector": sector_info.sector, "industry": sector_info.industry},
            )

        # Find all tickers in same industry
        industry_key = f"{sector_info.sector}::{sector_info.industry}"
        candidates = await self._get_industry_tickers(
            sector_info.sector, sector_info.industry
        )

        # Remove focus ticker from candidates
        candidates.discard(ticker)

        if not candidates:
            logger.warning(
                "no_peer_candidates_found",
                ticker=ticker,
                sector=sector_info.sector,
                industry=sector_info.industry,
            )
            return []

        # Fetch sector info for all candidates (with caching)
        candidate_info = await self._batch_get_sector_info(list(candidates))

        # Apply filters
        filters_applied = []
        filtered_candidates = []

        for candidate_ticker, info in candidate_info.items():
            # Skip if missing data
            if not info or not info.is_valid():
                continue

            # Country filter
            if same_country and sector_info.country:
                if info.country != sector_info.country:
                    continue
                if "same_country" not in filters_applied:
                    filters_applied.append("same_country")

            # Minimum market cap
            if min_market_cap and info.market_cap:
                if info.market_cap < min_market_cap:
                    continue
                if "min_market_cap" not in filters_applied:
                    filters_applied.append("min_market_cap")

            # Market cap ratio filter
            if sector_info.market_cap and info.market_cap:
                ratio = info.market_cap / sector_info.market_cap
                if ratio < self._min_market_cap_ratio or ratio > self._max_market_cap_ratio:
                    continue
                if "market_cap_ratio" not in filters_applied:
                    filters_applied.append("market_cap_ratio")

            filtered_candidates.append((candidate_ticker, info.market_cap or 0))

        # Sort by market cap (descending) and take top N
        filtered_candidates.sort(key=lambda x: x[1], reverse=True)
        peers = [t for t, _ in filtered_candidates[:max_peers]]

        logger.info(
            "peers_found",
            ticker=ticker,
            sector=sector_info.sector,
            industry=sector_info.industry,
            total_candidates=len(candidates),
            filtered_count=len(filtered_candidates),
            peers_returned=len(peers),
            filters=filters_applied,
        )

        return peers

    async def find_peers_by_sector(
        self,
        sector: str,
        industry: Optional[str] = None,
        max_results: int = 50,
    ) -> List[str]:
        """
        Get all tickers in a sector (optionally filtered by industry).

        Args:
            sector: The sector name (e.g., "Technology")
            industry: Optional industry name for filtering
            max_results: Maximum number of results

        Returns:
            List of ticker symbols in the sector/industry
        """
        logger.info(
            "finding_tickers_by_sector",
            sector=sector,
            industry=industry,
            max_results=max_results,
        )

        tickers = await self._get_industry_tickers(sector, industry)

        # Fetch info to filter out invalid tickers
        ticker_info = await self._batch_get_sector_info(list(tickers)[:max_results * 2])

        valid_tickers = [
            t for t, info in ticker_info.items()
            if info and info.is_valid() and info.sector == sector
            and (not industry or info.industry == industry)
        ]

        return valid_tickers[:max_results]

    async def get_sector_info(self, ticker: str) -> SectorInfo:
        """
        Get sector and industry information for a ticker.

        Args:
            ticker: The ticker symbol

        Returns:
            SectorInfo object with sector/industry data

        Raises:
            TickerNotFoundError: If ticker cannot be found
            DataFetchError: If sector data cannot be fetched
        """
        ticker = ticker.upper().strip()

        # Check cache
        if ticker in self._sector_cache:
            cached = self._sector_cache[ticker]
            if not cached.is_stale(self._cache_ttl_hours):
                logger.debug("sector_info_from_cache", ticker=ticker)
                return cached

        # Fetch from yfinance
        logger.info("fetching_sector_info", ticker=ticker)

        try:
            stock = yf.Ticker(ticker)
            info = await asyncio.to_thread(lambda: stock.info)

            if not info or "symbol" not in info:
                raise TickerNotFoundError(
                    f"Ticker {ticker} not found",
                    ticker=ticker,
                    sources_checked=["yfinance"],
                )

            sector_info = SectorInfo(
                ticker=ticker,
                sector=info.get("sector"),
                industry=info.get("industry"),
                country=info.get("country"),
                exchange=info.get("exchange"),
                market_cap=info.get("marketCap"),
                last_updated=datetime.utcnow(),
            )

            # Cache the result
            self._sector_cache[ticker] = sector_info

            logger.info(
                "sector_info_fetched",
                ticker=ticker,
                sector=sector_info.sector,
                industry=sector_info.industry,
                market_cap=sector_info.market_cap,
            )

            return sector_info

        except Exception as e:
            if isinstance(e, (TickerNotFoundError, DataFetchError)):
                raise
            raise DataFetchError(
                f"Failed to fetch sector info for {ticker}",
                source="yfinance",
                ticker=ticker,
                cause=e,
            )

    async def _batch_get_sector_info(
        self, tickers: List[str], max_concurrent: int = 10
    ) -> Dict[str, Optional[SectorInfo]]:
        """
        Fetch sector info for multiple tickers concurrently.

        Args:
            tickers: List of ticker symbols
            max_concurrent: Maximum concurrent requests

        Returns:
            Dict mapping ticker to SectorInfo (None if fetch failed)
        """
        logger.info("batch_fetching_sector_info", ticker_count=len(tickers))

        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(ticker: str):
            async with semaphore:
                try:
                    info = await self.get_sector_info(ticker)
                    return ticker, info
                except Exception as e:
                    logger.warning(
                        "batch_fetch_failed",
                        ticker=ticker,
                        error=str(e),
                    )
                    return ticker, None

        # Execute all fetches concurrently
        tasks = [fetch_with_semaphore(t) for t in tickers]
        fetch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in fetch_results:
            if isinstance(result, Exception):
                logger.error("batch_fetch_exception", error=str(result))
                continue
            ticker, info = result
            results[ticker] = info

        success_count = sum(1 for v in results.values() if v is not None)
        logger.info(
            "batch_fetch_complete",
            total=len(tickers),
            success=success_count,
            failed=len(tickers) - success_count,
        )

        return results

    async def _get_industry_tickers(
        self, sector: str, industry: Optional[str] = None
    ) -> Set[str]:
        """
        Get known tickers for a sector/industry.

        Note: This is a simplified implementation. In production, you might:
        - Maintain a database of sector/industry classifications
        - Use a third-party API for comprehensive ticker lists
        - Scrape exchange listings

        Args:
            sector: Sector name
            industry: Optional industry name

        Returns:
            Set of ticker symbols
        """
        # For now, we'll use a common ticker approach
        # In production, integrate with a ticker database or API

        # Common major tickers by sector (example seed data)
        SECTOR_SEEDS = {
            "Technology": [
                "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD", "INTC", "CSCO",
                "ORCL", "ADBE", "CRM", "AVGO", "QCOM", "TXN", "IBM", "NOW",
                "INTU", "AMAT", "MU", "ADI", "LRCX", "KLAC", "SNPS", "CDNS",
            ],
            "Consumer Cyclical": [
                "AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "TGT", "LOW", "TJX",
                "BKNG", "CMG", "MAR", "GM", "F", "ROST", "YUM", "DHI", "LEN",
            ],
            "Healthcare": [
                "UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "PFE", "DHR",
                "BMY", "AMGN", "CVS", "CI", "ELV", "MDT", "GILD", "REGN", "VRTX",
            ],
            "Financial Services": [
                "JPM", "V", "MA", "BAC", "WFC", "MS", "GS", "BLK", "SPGI", "C",
                "SCHW", "AXP", "CB", "PGR", "MMC", "ICE", "CME", "AON", "TFC",
            ],
            "Communication Services": [
                "GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS",
                "CHTR", "EA", "ATVI", "TTWO", "WBD", "PARA", "OMC", "IPG",
            ],
            "Consumer Defensive": [
                "WMT", "PG", "KO", "PEP", "COST", "PM", "MO", "EL", "MDLZ",
                "CL", "KMB", "GIS", "KHC", "K", "HSY", "CLX", "SJM", "CPB",
            ],
            "Industrials": [
                "UPS", "HON", "UNP", "BA", "RTX", "CAT", "GE", "DE", "LMT",
                "MMM", "FDX", "EMR", "ETN", "NSC", "GD", "NOC", "ITW", "CSX",
            ],
            "Energy": [
                "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY",
                "WMB", "KMI", "HAL", "BKR", "HES", "DVN", "FANG", "MRO", "APA",
            ],
            "Basic Materials": [
                "LIN", "APD", "SHW", "ECL", "NEM", "FCX", "DD", "DOW", "NUE",
                "VMC", "MLM", "PPG", "ALB", "CE", "FMC", "IFF", "EMN", "CF",
            ],
            "Real Estate": [
                "PLD", "AMT", "EQIX", "PSA", "O", "WELL", "DLR", "SPG", "AVB",
                "EQR", "VTR", "SBAC", "ARE", "INVH", "MAA", "ESS", "UDR", "EXR",
            ],
            "Utilities": [
                "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC",
                "ED", "ES", "PEG", "AWK", "DTE", "EIX", "PPL", "FE", "AEE",
            ],
        }

        # Get seed tickers for the sector
        seed_tickers = set(SECTOR_SEEDS.get(sector, []))

        # If we have cached industry data, return it
        industry_key = f"{sector}::{industry}" if industry else sector
        if industry_key in self._industry_tickers:
            cached = self._industry_tickers[industry_key]
            if len(cached) > 5:  # Only use cache if it has meaningful data
                return cached

        # Expand using cached sector info
        for ticker, info in self._sector_cache.items():
            if info.sector == sector:
                if not industry or info.industry == industry:
                    seed_tickers.add(ticker)

        # Cache the result
        self._industry_tickers[industry_key] = seed_tickers

        return seed_tickers

    def clear_cache(self):
        """Clear all cached sector and industry data."""
        self._sector_cache.clear()
        self._industry_tickers.clear()
        logger.info("peer_finder_cache_cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "sector_info_cached": len(self._sector_cache),
            "industry_groups_cached": len(self._industry_tickers),
            "total_tickers": sum(len(v) for v in self._industry_tickers.values()),
        }
