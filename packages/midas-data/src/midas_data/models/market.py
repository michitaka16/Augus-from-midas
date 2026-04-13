"""
Market data models — bars, fundamentals, corporate actions, ETF universe.

These are the shared data fabric tables. Every user sees the same market data
(no user_id column). This is intentional — the publisher exemption requires
impersonal data delivery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Bar:
    """OHLCV bar for an ETF. TimescaleDB hypertable, partitioned by date."""

    id: int = field(default=0, metadata={"primary_key": True})
    ticker: str = field(default="", metadata={"max_length": 20, "index": True})
    date: date = field(default_factory=date.today, metadata={"index": True})
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    adj_close: float = 0.0
    volume: int = 0
    source: str = field(default="eodhd", metadata={"max_length": 20})
    ingested_at: datetime = field(default_factory=datetime.utcnow)

    class Meta:
        unique_together = [("ticker", "date", "source")]


@dataclass
class Fundamental:
    """Point-in-time fundamental data. Keyed by (ticker, report_date, as_of_date, field_name)."""

    id: int = field(default=0, metadata={"primary_key": True})
    ticker: str = field(default="", metadata={"max_length": 20, "index": True})
    report_date: date = field(default_factory=date.today)
    as_of_date: date = field(default_factory=date.today)
    field_name: str = field(default="", metadata={"max_length": 100})
    value: float = 0.0
    source: str = field(default="eodhd", metadata={"max_length": 20})

    class Meta:
        unique_together = [("ticker", "report_date", "as_of_date", "field_name")]


@dataclass
class CorpAction:
    """Corporate actions (splits, dividends, mergers) for survivorship-free backtests."""

    id: int = field(default=0, metadata={"primary_key": True})
    ticker: str = field(default="", metadata={"max_length": 20, "index": True})
    ex_date: date = field(default_factory=date.today, metadata={"index": True})
    action_type: str = field(default="", metadata={"max_length": 20})
    factor: float = 1.0
    announced_date: Optional[date] = None
    source: str = field(default="eodhd", metadata={"max_length": 20})


@dataclass
class EtfUniverse:
    """Point-in-time ETF universe for survivorship-free backtests.

    For any historical date, query WHERE inception_date <= date AND
    (delist_date IS NULL OR delist_date > date) to get the ETFs
    that were tradeable on that date.
    """

    id: int = field(default=0, metadata={"primary_key": True})
    ticker: str = field(default="", metadata={"max_length": 20, "index": True})
    name: str = field(default="", metadata={"max_length": 200})
    inception_date: date = field(default_factory=date.today)
    delist_date: Optional[date] = None
    sleeve: str = field(default="", metadata={"max_length": 50, "index": True})
    expense_ratio: float = 0.0
    avg_daily_volume: int = 0
    liquidity_tier: str = field(default="high", metadata={"max_length": 10})
    is_active: bool = True
