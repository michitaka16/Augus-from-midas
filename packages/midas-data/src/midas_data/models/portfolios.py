"""
Model portfolio definitions — the 5 published portfolios.

These are configuration records, not user-specific.
Part of the impersonal publisher model (ADR-001).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelPortfolio:
    """A model portfolio with its vol target and pricing."""

    id: str = field(default="", metadata={"primary_key": True, "max_length": 50})
    name: str = field(default="", metadata={"max_length": 100})
    description: str = field(default="")
    vol_target: float = 0.0
    style: str = field(default="", metadata={"max_length": 50})
    monthly_price_usd: float = 0.0
    is_active: bool = True


# Default portfolio definitions — seeded on first migration
DEFAULT_PORTFOLIOS = [
    ModelPortfolio(
        id="aggressive_growth",
        name="Aggressive Growth",
        description="Maximum growth with 18% vol target. Full allocation to highest-momentum sleeves in normal regime.",
        vol_target=18.0,
        style="aggressive_growth",
        monthly_price_usd=29.0,
        is_active=True,
    ),
    ModelPortfolio(
        id="growth",
        name="Growth",
        description="Strong growth with 14% vol target. Diversified across top momentum sleeves.",
        vol_target=14.0,
        style="growth",
        monthly_price_usd=29.0,
        is_active=True,
    ),
    ModelPortfolio(
        id="balanced",
        name="Balanced",
        description="Balanced risk-return with 10% vol target. Mix of equity, bonds, and alternatives.",
        vol_target=10.0,
        style="balanced",
        monthly_price_usd=19.0,
        is_active=True,
    ),
    ModelPortfolio(
        id="conservative",
        name="Conservative",
        description="Capital preservation with 6% vol target. Heavy bond and dividend allocation.",
        vol_target=6.0,
        style="conservative",
        monthly_price_usd=9.0,
        is_active=True,
    ),
    ModelPortfolio(
        id="income",
        name="Income",
        description="Income-focused with 6% vol target. Dividend ETFs, REITs, and high-quality bonds.",
        vol_target=6.0,
        style="income",
        monthly_price_usd=19.0,
        is_active=True,
    ),
]
