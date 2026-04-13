"""
Signal models — regime signals, published signals, signal inputs, backtest runs.

CRITICAL: The `signals` table has NO user_id column. This is the structural
enforcement of the publisher exemption (ADR-001, TC1 resolution). The
midas_publisher Postgres role cannot SELECT from the users schema. A boot-time
assertion and CI check enforce this (ADR-009, M06-05/M06-06).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class RegimeSignal:
    """Raw regime signal values from FRED, IBKR, or computed indicators."""

    id: int = field(default=0, metadata={"primary_key": True})
    date: date = field(default_factory=date.today, metadata={"index": True})
    signal_name: str = field(default="", metadata={"max_length": 50, "index": True})
    value: float = 0.0
    ensemble_score: Optional[float] = None
    regime: Optional[str] = field(default=None, metadata={"max_length": 20})
    source: str = field(default="", metadata={"max_length": 20})

    class Meta:
        unique_together = [("date", "signal_name")]


@dataclass
class Signal:
    """Published signal for a model portfolio.

    NO user_id — this is impersonal, same for all subscribers.
    Keyed by (model_portfolio_id, timestamp).
    """

    id: int = field(default=0, metadata={"primary_key": True})
    model_portfolio_id: str = field(default="", metadata={"max_length": 50, "index": True})
    timestamp: datetime = field(default_factory=datetime.utcnow, metadata={"index": True})
    regime: str = field(default="normal", metadata={"max_length": 20})
    allocations_json: str = field(default="{}")
    reasoning_json: str = field(default="{}")
    cost_estimate_json: str = field(default="{}")
    ensemble_score: float = 0.0
    published: bool = False
    published_at: Optional[datetime] = None

    class Meta:
        unique_together = [("model_portfolio_id", "timestamp")]


@dataclass
class SignalInput:
    """Immutable snapshot of exact input data consumed by a live signal run.

    Used by the nightly replay job (M03-04) to reproduce signals against the
    EXACT data the live run consumed, not current corrected data (TC2 resolution).
    """

    id: int = field(default=0, metadata={"primary_key": True})
    signal_id: int = field(default=0, metadata={"index": True})
    snapshot_json: str = field(default="{}")
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BacktestRun:
    """Backtest run results. Cited by the debate agent via backtest_run_id."""

    id: int = field(default=0, metadata={"primary_key": True})
    model_portfolio_id: str = field(default="", metadata={"max_length": 50, "index": True})
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    config_json: str = field(default="{}")
    results_json: str = field(default="{}")
    horizons_json: str = field(default="[]")
    regime_stats_json: str = field(default="[]")
    benchmarks_json: str = field(default="[]")
    deflated_sharpe: Optional[float] = None
    pbo: Optional[float] = None
    worst_12m_return: Optional[float] = None
    status: str = field(default="running", metadata={"max_length": 20})
