"""Tier 1 unit tests for PIT universe manager logic.

Note: The actual PITUniverseManager requires a database connection.
These tests verify the validation logic using a mock connection.
Full integration tests in test_integration.py (Tier 2).
"""

from datetime import date

import pytest


@pytest.mark.unit
def test_sleeve_etf_definitions_complete():
    """Verify that the historical load script covers all 8+ sleeves."""
    from scripts.load_historical import SLEEVE_ETFS

    expected_sleeves = {
        "equity_sector",
        "precious_metals",
        "govt_bonds_short",
        "govt_bonds_intermediate",
        "govt_bonds_long",
        "ig_corp_bonds",
        "reits",
        "commodities",
        "dividend_etfs",
        "em_equity",
    }
    assert set(SLEEVE_ETFS.keys()) == expected_sleeves


@pytest.mark.unit
def test_each_sleeve_has_at_least_2_etfs():
    """Each sleeve should have at least 2 ETFs for diversification."""
    from scripts.load_historical import SLEEVE_ETFS

    for sleeve, etfs in SLEEVE_ETFS.items():
        assert len(etfs) >= 2, f"Sleeve '{sleeve}' has only {len(etfs)} ETF(s)"


@pytest.mark.unit
def test_fred_series_covers_all_regime_signals():
    """Verify FRED series covers the regime detection ensemble inputs."""
    from scripts.load_historical import FRED_SERIES

    required = {"vix", "hy_oas", "yield_3m", "yield_10y"}
    assert required.issubset(set(FRED_SERIES.keys()))
