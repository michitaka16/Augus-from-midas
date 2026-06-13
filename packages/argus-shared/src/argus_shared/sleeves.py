"""
Asset sleeve definitions — the 10 sleeves that make up Midas portfolios.

Each sleeve has representative ETF tickers, expense ratios, and a liquidity tier.

Moved from midas-strategy/src/midas_strategy/sleeves/__init__.py
Midas-specific trading code (allocator, signals, IBKR, OAuth) NOT included.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ETFDef:
    """An ETF within a sleeve."""

    ticker: str
    name: str
    expense_ratio: float  # in basis points (e.g., 0.09 = 9 bps)
    avg_daily_volume: int  # shares
    liquidity_tier: str  # "high", "medium", "low"


@dataclass(frozen=True)
class SleeveDef:
    """An asset sleeve with its representative ETFs."""

    id: str
    name: str
    description: str
    etfs: tuple[ETFDef, ...]
    primary_ticker: str


SLEEVES: dict[str, SleeveDef] = {
    "equity_sector": SleeveDef(
        id="equity_sector",
        name="Equity Sectors",
        description="US equity sector rotation via SPDR sector ETFs",
        primary_ticker="SPY",
        etfs=(
            ETFDef("SPY", "SPDR S&P 500 ETF", 0.0945, 80_000_000, "high"),
            ETFDef("QQQ", "Invesco QQQ Trust", 0.20, 50_000_000, "high"),
            ETFDef("XLF", "Financial Select Sector SPDR", 0.09, 30_000_000, "high"),
        ),
    ),
    "precious_metals": SleeveDef(
        id="precious_metals",
        name="Precious Metals",
        description="Gold and silver exposure",
        primary_ticker="GLD",
        etfs=(
            ETFDef("GLD", "SPDR Gold Shares", 0.40, 10_000_000, "high"),
            ETFDef("SLV", "iShares Silver Trust", 0.50, 15_000_000, "high"),
        ),
    ),
    "govt_bonds_short": SleeveDef(
        id="govt_bonds_short",
        name="Short-Term Government Bonds",
        description="1-3 year US Treasury bonds",
        primary_ticker="SHY",
        etfs=(
            ETFDef("SHY", "iShares 1-3 Year Treasury Bond", 0.15, 5_000_000, "high"),
            ETFDef("SHV", "iShares Short Treasury Bond", 0.15, 3_000_000, "high"),
        ),
    ),
    "govt_bonds_intermediate": SleeveDef(
        id="govt_bonds_intermediate",
        name="Intermediate Government Bonds",
        description="3-10 year US Treasury bonds",
        primary_ticker="IEF",
        etfs=(
            ETFDef("IEF", "iShares 7-10 Year Treasury Bond", 0.15, 8_000_000, "high"),
            ETFDef("IEI", "iShares 3-7 Year Treasury Bond", 0.15, 4_000_000, "high"),
        ),
    ),
    "govt_bonds_long": SleeveDef(
        id="govt_bonds_long",
        name="Long-Term Government Bonds",
        description="20+ year US Treasury bonds",
        primary_ticker="TLT",
        etfs=(
            ETFDef("TLT", "iShares 20+ Year Treasury Bond", 0.15, 15_000_000, "high"),
            ETFDef("TLH", "iShares 10-20 Year Treasury Bond", 0.15, 2_000_000, "medium"),
        ),
    ),
    "ig_corp_bonds": SleeveDef(
        id="ig_corp_bonds",
        name="Investment-Grade Corporate Bonds",
        description="High-quality corporate bonds",
        primary_ticker="LQD",
        etfs=(
            ETFDef("LQD", "iShares iBoxx IG Corporate Bond", 0.14, 10_000_000, "high"),
            ETFDef("VCIT", "Vanguard Intermediate-Term Corporate Bond", 0.04, 5_000_000, "high"),
        ),
    ),
    "reits": SleeveDef(
        id="reits",
        name="REITs",
        description="US real estate investment trusts",
        primary_ticker="VNQ",
        etfs=(
            ETFDef("VNQ", "Vanguard Real Estate ETF", 0.12, 5_000_000, "high"),
            ETFDef("IYR", "iShares U.S. Real Estate ETF", 0.39, 4_000_000, "high"),
        ),
    ),
    "commodities": SleeveDef(
        id="commodities",
        name="Commodities",
        description="Broad commodity exposure",
        primary_ticker="DJP",
        etfs=(
            ETFDef("DJP", "iPath Bloomberg Commodity Index", 0.70, 3_000_000, "medium"),
            ETFDef("GSG", "iShares S&P GSCI Commodity ETF", 0.75, 2_000_000, "medium"),
            ETFDef("DBC", "Invesco DB Commodity Index", 0.87, 2_000_000, "medium"),
        ),
    ),
    "dividend_etfs": SleeveDef(
        id="dividend_etfs",
        name="Dividend ETFs",
        description="High-yield dividend equity",
        primary_ticker="VYM",
        etfs=(
            ETFDef("VYM", "Vanguard High Dividend Yield ETF", 0.06, 3_000_000, "high"),
            ETFDef("DVY", "iShares Select Dividend ETF", 0.38, 2_000_000, "medium"),
            ETFDef("SDY", "SPDR S&P Dividend ETF", 0.35, 1_500_000, "medium"),
        ),
    ),
    "em_equity": SleeveDef(
        id="em_equity",
        name="Emerging Markets Equity",
        description="Broad emerging markets equity exposure",
        primary_ticker="VWO",
        etfs=(
            ETFDef("VWO", "Vanguard FTSE Emerging Markets ETF", 0.08, 10_000_000, "high"),
            ETFDef("EEM", "iShares MSCI Emerging Markets ETF", 0.68, 20_000_000, "high"),
        ),
    ),
}


def get_sleeve(sleeve_id: str) -> SleeveDef:
    """Get a sleeve definition by ID. Raises KeyError if not found."""
    return SLEEVES[sleeve_id]


def get_all_sleeves() -> list[SleeveDef]:
    """Get all sleeve definitions."""
    return list(SLEEVES.values())


def get_primary_tickers() -> dict[str, str]:
    """Map sleeve_id → primary ticker for each sleeve."""
    return {s.id: s.primary_ticker for s in SLEEVES.values()}


def get_all_tickers() -> list[str]:
    """Get all unique tickers across all sleeves."""
    tickers = set()
    for sleeve in SLEEVES.values():
        for etf in sleeve.etfs:
            tickers.add(etf.ticker)
    return sorted(tickers)


def get_liquidity_tier(ticker: str) -> str:
    """Get the liquidity tier for a ticker. Returns 'unknown' if not found."""
    for sleeve in SLEEVES.values():
        for etf in sleeve.etfs:
            if etf.ticker == ticker:
                return etf.liquidity_tier
    return "unknown"
