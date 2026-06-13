"""
dash_app.py — Argus ETF Compliance & Recommendation Dashboard.

Multi-page Dash app:
  PAGE 1 — Compliance Editor: preset buttons, custom constraints,
           portfolio entry, traffic-light per ETF, overall score
  PAGE 2 — xray_map: Plotly UMAP 2D scatter colored by cluster,
           user's ETFs highlighted, violations in red / compliant in green
  PAGE 3 — Recommend: top-3 alternatives per violating ETF from
           the same cluster, using cosine similarity in original feature space

Run:
    cd apps/argus
    python dash_app.py          # starts on http://127.0.0.1:8050
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import csv
import json
from pathlib import Path

# ── Dash 4.1.0 Bug Workaround ─────────────────────────────────────────────────
# Dash 4.1.0 sends pattern-matching IDs as dict objects in changedPropIds
# from the React client, but the Python backend tries to use them as dict keys
# without stringifying first → TypeError: cannot use 'dict' as a dict key.
# Monkey-patch _initialize_context to stringify dict-type IDs.
import dash.dash as _dash_module
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import (
    ALL,
    Dash,
    Input,
    Output,
    State,
    callback_context,
    dcc,
    html,
)
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

_orig_init_ctx = _dash_module.Dash._initialize_context


def _patched_init_context(self, body):
    if body and isinstance(body, dict) and "changedPropIds" in body:
        fixed = dict(body)
        fixed["changedPropIds"] = [
            str(x) if isinstance(x, dict) else x for x in body["changedPropIds"]
        ]
        return _orig_init_ctx(self, fixed)
    return _orig_init_ctx(self, body)


_dash_module.Dash._initialize_context = _patched_init_context

# ── Data Loading ───────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR


def _load_universe() -> pd.DataFrame:
    df = pd.read_csv(CACHE_DIR / "etf_universe.csv")
    df = df.set_index("ticker")
    return df


def _load_features9() -> pd.DataFrame:
    """9-feature DataFrame used for clustering + similarity (from etf_xray_features).

    Feature set: country_exposure, sector_exposure, expense_ratio,
    volatility_252d, momentum_126d, liquidity, yield, corr_to_spy,
    asset_class_equity (max_drawdown_252d and is_leveraged are dropped;
    asset_class_equity replaces is_leveraged per decisions 0005/000006).
    """
    df = pd.read_csv(CACHE_DIR / "etf_xray_features.csv", index_col=0)
    df = df.drop(columns=["is_leveraged"], errors="ignore")
    df["asset_class_equity"] = _universe["asset_class_equity"]
    FEAT9 = [
        "country_exposure",
        "sector_exposure",
        "expense_ratio",
        "volatility_252d",
        "momentum_126d",
        "liquidity",
        "yield",
        "corr_to_spy",
        "asset_class_equity",
    ]
    return df[FEAT9]


def _load_raw_features() -> pd.DataFrame:
    """Unstandardized feature values needed for constraint evaluation."""
    # Rebuild from the same logic as clustering.py / recommender.py
    prices, stats = {}, {}
    with open(CACHE_DIR / "etf_prices.csv") as f:
        for row in csv.DictReader(f):
            ticker = row.pop("ticker")
            prices[ticker] = [float(v) for v in row.values() if v]
    with open(CACHE_DIR / "etf_stats.csv") as f:
        for row in csv.DictReader(f):
            stats[row["ticker"]] = {
                "expense_ratio": float(row.get("expense_ratio", 0)),
                "dividend_yield": float(row.get("dividend_yield", 0)),
                "aum": float(row.get("aum", 0)),
                "avg_volume": int(row.get("avg_volume", 0)),
            }

    SLEEVE_EXPENSE_RATIOS = {
        "SPY": 0.0945,
        "QQQ": 0.20,
        "XLF": 0.09,
        "GLD": 0.40,
        "SLV": 0.50,
        "SHY": 0.15,
        "SHV": 0.15,
        "IEF": 0.15,
        "IEI": 0.15,
        "TLT": 0.15,
        "TLH": 0.15,
        "LQD": 0.14,
        "VCIT": 0.04,
        "VNQ": 0.12,
        "IYR": 0.39,
        "DJP": 0.70,
        "GSG": 0.75,
        "DBC": 0.87,
        "VYM": 0.06,
        "DVY": 0.38,
        "SDY": 0.35,
        "VWO": 0.08,
        "EEM": 0.68,
    }
    COUNTRY_EXPOSURE = {
        "VTI": 1.0,
        "VOO": 1.0,
        "SPY": 1.0,
        "QQQ": 1.0,
        "IWM": 1.0,
        "VIG": 1.0,
        "SCHD": 1.0,
        "ESGU": 1.0,
        "XLK": 1.0,
        "XLF": 1.0,
        "XLE": 1.0,
        "XLV": 1.0,
        "XLI": 1.0,
        "VEA": 0.0,
        "EFA": 0.0,
        "VWO": 0.0,
        "EEM": 0.0,
        "BND": 1.0,
        "AGG": 1.0,
        "TLT": 1.0,
        "LQD": 1.0,
        "GLD": 1.0,
        "SLV": 1.0,
    }
    SECTOR_EXPOSURE = {
        "VTI": 0.3,
        "VOO": 0.3,
        "SPY": 0.3,
        "QQQ": 0.5,
        "XLK": 0.9,
        "IWM": 0.4,
        "VIG": 0.4,
        "SCHD": 0.4,
        "VEA": 0.0,
        "VWO": 0.0,
        "EEM": 0.0,
        "EFA": 0.0,
        "XLF": 0.8,
        "XLE": 0.9,
        "XLV": 0.9,
        "XLI": 0.9,
        "BND": 0.0,
        "AGG": 0.0,
        "TLT": 0.0,
        "LQD": 0.0,
        "GLD": 0.0,
        "SLV": 0.0,
        "ESGU": 0.3,
    }

    tickers = sorted(prices.keys())
    feat_names = [
        "country_exposure",
        "sector_exposure",
        "expense_ratio",
        "volatility_252d",
        "momentum_126d",
        "liquidity",
        "yield",
        "corr_to_spy",
    ]
    raw = {f: [] for f in feat_names}
    spy_prices = prices.get("SPY", [])
    spy_rets = (
        np.diff(spy_prices) / np.array(spy_prices[:-1]) if len(spy_prices) > 1 else np.array([])
    )

    for ticker in tickers:
        p = np.array(prices[ticker])
        rets = np.diff(p) / p[:-1] if len(p) > 1 else np.array([])
        s = stats.get(ticker, {})
        raw["country_exposure"].append(COUNTRY_EXPOSURE.get(ticker, 0.5))
        raw["sector_exposure"].append(SECTOR_EXPOSURE.get(ticker, 0.0))
        er = s.get("expense_ratio", 0.0)
        if er == 0.0:
            er = SLEEVE_EXPENSE_RATIOS.get(ticker, 0.001)
        raw["expense_ratio"].append(er)
        raw["volatility_252d"].append(
            float(np.std(rets) * np.sqrt(252)) if len(rets) >= 20 else 0.0
        )
        if len(rets) >= 126:
            raw["momentum_126d"].append(float(np.prod(1 + rets[-126:]) - 1))
        elif len(rets) >= 20:
            raw["momentum_126d"].append(float(np.prod(1 + rets) - 1))
        else:
            raw["momentum_126d"].append(0.0)
        aum = s.get("aum", 1.0)
        avg_vol = s.get("avg_volume", 0)
        last_price = float(p[-1]) if len(p) > 0 else 0.0
        liq = (avg_vol * last_price / (aum * 1e9)) if aum > 0 and avg_vol > 0 else 0.0
        raw["liquidity"].append(liq)
        raw["yield"].append(s.get("dividend_yield", 0.0))
        if len(rets) >= 126 and len(spy_rets) >= 126:
            er126, sr = rets[-126:], spy_rets[-126:]
            corr = (
                float(np.corrcoef(er126, sr)[0, 1]) if np.std(er126) > 0 and np.std(sr) > 0 else 0.0
            )
        else:
            corr = 0.0
        raw["corr_to_spy"].append(corr if np.isfinite(corr) else 0.0)

    return pd.DataFrame(raw, index=tickers).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def _load_umap_coords() -> pd.DataFrame:
    return pd.read_csv(CACHE_DIR / "umap_coords.csv", index_col=0)


def _load_xray_data() -> pd.DataFrame:
    """Enriched ETF data for the X-ray panel: country/sector breakdowns, top holdings."""
    df = pd.read_csv(CACHE_DIR / "etf_xray_data.csv", index_col=0)
    df.index.name = "ticker"
    return df


_xray_data = _load_xray_data()


# ── Holdings Cache ──────────────────────────────────────────────────────────────

_holdings_cache: dict[str, dict] = {}


def get_etf_holdings(ticker: str) -> dict:
    """Fetch top 10 ETF holdings from yfinance. Cached per session."""
    if ticker in _holdings_cache:
        return _holdings_cache[ticker]

    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        fd = t.funds_data
        top_holdings = fd.top_holdings

        if top_holdings is None or top_holdings.empty:
            _holdings_cache[ticker] = {"error": "No holdings data available"}
            return _holdings_cache[ticker]

        # sector_weightings at ETF level
        sector_weightings = fd.sector_weightings or {}

        _holdings_cache[ticker] = {
            "holdings": top_holdings,
            "sectors": sector_weightings,
        }
        return _holdings_cache[ticker]
    except Exception as e:
        _holdings_cache[ticker] = {"error": str(e)}
        return _holdings_cache[ticker]


def _build_xray_panel(ticker: str) -> html.Div:
    """Expandable X-ray detail panel for a single ETF."""
    if ticker not in _xray_data.index:
        return html.Div()

    row = _xray_data.loc[ticker]

    # Country breakdown table
    country_rows = []
    for col, label in [
        ("us_pct", "United States"),
        ("china_pct", "China"),
        ("europe_pct", "Europe"),
        ("japan_pct", "Japan"),
        ("emerging_pct", "Emerging Markets"),
    ]:
        val = float(row.get(col, 0) or 0)
        if val > 0:
            country_rows.append(
                html.Tr([html.Td(label), html.Td(f"{val:.1f}%"), html.Td(_make_bar_cell(val))])
            )

    # Sector breakdown table
    sector_rows = []
    for col, label in [
        ("tech_pct", "Technology"),
        ("finance_pct", "Financials"),
        ("healthcare_pct", "Healthcare"),
        ("energy_pct", "Energy"),
        ("consumer_pct", "Consumer"),
        ("industrial_pct", "Industrials"),
        ("materials_pct", "Materials"),
        ("other_pct", "Other"),
    ]:
        val = float(row.get(col, 0) or 0)
        if val > 0:
            sector_rows.append(
                html.Tr([html.Td(label), html.Td(f"{val:.1f}%"), html.Td(_make_bar_cell(val))])
            )

    # 9 raw features (from _raw_feats)
    raw_row = _raw_feats.loc[ticker] if ticker in _raw_feats.index else None
    feat_rows = []
    if raw_row is not None:
        feat_labels = {
            "country_exposure": "Country Exposure",
            "sector_exposure": "Sector Exposure",
            "expense_ratio": "Expense Ratio",
            "volatility_252d": "Volatility (252d)",
            "momentum_126d": "Momentum (126d)",
            "liquidity": "Liquidity",
            "yield": "Dividend Yield",
            "corr_to_spy": "Corr. to SPY",
        }
        for col, label in feat_labels.items():
            val = float(raw_row.get(col, 0) or 0)
            feat_rows.append(html.Tr([html.Td(label), html.Td(f"{val:.4f}")]))

    # Holdings data (live from yfinance — fetched per click)
    holdings_data = get_etf_holdings(ticker)
    holdings_error = holdings_data.get("error")

    if holdings_error:
        holdings_section = html.Small(
            "Holdings data unavailable for this ETF",
            style={"color": "#999", "fontStyle": "italic"},
        )
    else:
        top_holdings = holdings_data.get("holdings")
        sector_w = holdings_data.get("sectors", {})

        if top_holdings is not None and not top_holdings.empty:
            hold_rows = []
            for symbol, row_h in top_holdings.iterrows():
                pct = float(row_h.get("Holding Percent", 0)) * 100
                name = str(row_h.get("Name", symbol))
                hold_rows.append(
                    html.Tr(
                        [
                            html.Td(symbol, style={"fontWeight": "bold", "fontSize": "12px"}),
                            html.Td(name[:30], style={"fontSize": "12px"}),
                            html.Td(
                                f"{pct:.2f}%", style={"fontSize": "12px", "textAlign": "right"}
                            ),
                        ]
                    )
                )
            holdings_table = dbc.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Symbol", style={"fontSize": "11px"}),
                                html.Th("Name", style={"fontSize": "11px"}),
                                html.Th("%", style={"fontSize": "11px", "textAlign": "right"}),
                            ]
                        )
                    ),
                    html.Tbody(hold_rows),
                ],
                bordered=False,
                size="sm",
                style={"marginBottom": 0},
            )

            # ETF sector weightings
            sector_rows_h = []
            sector_label_map = {
                "technology": "Technology",
                "financial_services": "Financials",
                "healthcare": "Healthcare",
                "energy": "Energy",
                "consumer_cyclical": "Consumer",
                "industrials": "Industrials",
                "basic_materials": "Materials",
                "realestate": "Real Estate",
                "utilities": "Utilities",
                "communication_services": "Comm.",
                "consumer_defensive": "Consumer Defensive",
            }
            for sec_key, sec_val in sector_w.items():
                label = sector_label_map.get(sec_key, sec_key.replace("_", " ").title())
                pct_v = float(sec_val) * 100
                if pct_v > 0:
                    sector_rows_h.append(
                        html.Tr(
                            [
                                html.Td(label, style={"fontSize": "11px"}),
                                html.Td(
                                    f"{pct_v:.1f}%",
                                    style={"fontSize": "11px", "textAlign": "right"},
                                ),
                                html.Td(_make_bar_cell(pct_v)),
                            ]
                        )
                    )

            sec_table = (
                dbc.Table(
                    [
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th("Sector (ETF-level)", style={"fontSize": "11px"}),
                                    html.Th("%", style={"fontSize": "11px", "textAlign": "right"}),
                                    html.Th("", style={"width": "80px"}),
                                ]
                            )
                        ),
                        html.Tbody(sector_rows_h),
                    ],
                    bordered=False,
                    size="sm",
                )
                if sector_rows_h
                else html.Small("No sector data", style={"color": "#999"})
            )

            holdings_section = html.Div(
                [
                    html.Strong("Top 10 Holdings", style={"fontSize": "11px", "color": "#555"}),
                    holdings_table,
                    html.Hr(style={"margin": "4px 0"}),
                    html.Strong("ETF Sector Weights", style={"fontSize": "11px", "color": "#555"}),
                    sec_table,
                ]
            )
        else:
            holdings_section = html.Small(
                "Holdings data not available for this ETF",
                style={"color": "#999", "fontStyle": "italic"},
            )

    return html.Div(
        [
            dbc.Row(
                [
                    # Country breakdown
                    dbc.Col(
                        [
                            html.Strong("Country Exposure"),
                            dbc.Table(
                                [html.Tbody(country_rows)] if country_rows else [],
                                bordered=False,
                                size="sm",
                                style={"marginBottom": 0},
                            ),
                        ],
                        width=4,
                    ),
                    # Sector breakdown
                    dbc.Col(
                        [
                            html.Strong("Sector Breakdown"),
                            dbc.Table(
                                [html.Tbody(sector_rows)] if sector_rows else [],
                                bordered=False,
                                size="sm",
                                style={"marginBottom": 0},
                            ),
                        ],
                        width=5,
                    ),
                    # Stats + Holdings button
                    dbc.Col(
                        [
                            html.Strong("Key Stats"),
                            dbc.ListGroup(
                                [
                                    dbc.ListGroupItem(
                                        f"Expense Ratio: {float(row.get('expense_ratio', 0)):.2f}%"
                                    ),
                                    dbc.ListGroupItem(
                                        f"Dividend Yield: {float(row.get('dividend_yield', 0)):.2f}%"
                                    ),
                                    dbc.ListGroupItem(f"AUM: ${float(row.get('aum_b', 0)):.0f}B"),
                                    dbc.ListGroupItem(
                                        f"Avg Volume: {int(float(row.get('avg_volume', 0))):,}"
                                    ),
                                ],
                                size="sm",
                            ),
                            # View Holdings toggle
                            html.Div(
                                html.Details(
                                    [
                                        html.Summary(
                                            "View Holdings",
                                            style={
                                                "cursor": "pointer",
                                                "list-style": "none",
                                                "fontSize": "12px",
                                                "color": "#007bff",
                                            },
                                        ),
                                        html.Div(holdings_section, style={"marginTop": 6}),
                                    ],
                                ),
                                style={"marginTop": 6},
                            ),
                        ],
                        width=3,
                    ),
                ],
                style={"padding": "8px 0"},
            ),
            html.Hr(style={"margin": "4px 0"}),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Strong("9 Features (Clustering + Similarity)"),
                            dbc.Table(
                                [html.Tbody(feat_rows)] if feat_rows else [],
                                bordered=False,
                                size="sm",
                            ),
                        ],
                        width=12,
                    ),
                ]
            ),
        ],
        style={"background": "#fafafa", "padding": "8px 12px", "borderRadius": "4px"},
    )


def _make_bar_cell(pct: float) -> html.Div:
    """Inline progress bar cell."""
    pct = max(0, min(100, pct))
    return html.Div(
        dbc.Progress(
            value=pct,
            bar=True,
            style={"height": "6px", "width": "80px"},
            color="primary",
        ),
        title=f"{pct:.1f}%",
    )


def _load_cluster_labels(k: int = 5) -> dict[str, int]:
    with open(CACHE_DIR / "cluster_results.json") as f:
        data = json.load(f)
    labels = data["k_results"][str(k)]["labels"]
    return dict(zip(data["tickers"], labels, strict=True))


# K=5 cluster → display name (human-curated)
CLUSTER_NAMES: dict[int, str] = {
    0: "Dividend & Yield Equity",
    1: "US Broad Equity",
    2: "Precious Metals",
    3: "Fixed Income",
    4: "International Equity",
}


def _load_presets() -> dict:
    with open(CACHE_DIR / "presets.json") as f:
        return json.load(f)


# Load static data at module import
_universe = _load_universe()
_features9 = _load_features9()
_raw_feats = _load_raw_features()
_umap_coords = _load_umap_coords()
_cluster_labels = _load_cluster_labels(k=5)
_presets = _load_presets()
ALL_TICKERS = sorted(_universe.index.tolist())

# Build ALL_* lists dynamically from presets for pattern-matching callbacks
ALL_CONSTRAINT_IDS = ["country_exposure"]
_sector_ids = set()
for preset_data in _presets["presets"].values():
    hard = preset_data.get("constraints", {}).get("hard", {})
    soft = preset_data.get("constraints", {}).get("soft", {})
    sector_hard = hard.get("sector_exposure", {}).get("max", {})
    sector_soft = soft.get("sector_exposure", {}).get("max", {})
    for s in list(sector_hard.keys()) + list(sector_soft.keys()):
        _sector_ids.add(s)
ALL_CONSTRAINT_IDS += [f"sector_exposure_{s}" for s in sorted(_sector_ids)]
ALL_HARD_COUNTRY_IDS: list[str] = []
ALL_SOFT_COUNTRY_IDS: list[str] = []
for preset_data in _presets["presets"].values():
    impl = preset_data.get("_impl", {})
    for cid in impl.get("hard_countries", {}):
        if cid not in ALL_HARD_COUNTRY_IDS:
            ALL_HARD_COUNTRY_IDS.append(cid)
    for cid in impl.get("soft_countries", {}):
        if cid not in ALL_SOFT_COUNTRY_IDS:
            ALL_SOFT_COUNTRY_IDS.append(cid)

# Ordered list of all ethical category IDs (used for ALL pattern callbacks)
ALL_CAT_IDS: list[str] = []
for preset_data in _presets["presets"].values():
    for cat_id in preset_data.get("_impl", {}).get("categories", {}):
        if cat_id not in ALL_CAT_IDS:
            ALL_CAT_IDS.append(cat_id)

# Preset rationale content (shown in View Rationale panel)
PRESET_RATIONALE = {
    "ethical_investor": {
        "concept": "Excludes sectors that violate common ethical standards — weapons, tobacco, gambling, alcohol, fossil fuels, and adult content.",
        "target": "Faith-based investors, values-driven retail investors, ESG-motivated retail investors.",
        "criteria": "Hard exclusions (weapons, fossil fuels) trigger immediate RED. Soft exclusions (tobacco, gambling, alcohol) are warnings only. Adult content shows informational note.",
        "roadmap": "Commercial: MSCI ESG controversy scores, Sustainalytics data, Sin Stock database for real-time exclusion flags.",
    },
    "climate_first": {
        "concept": "Excludes fossil fuel producers and high-carbon sectors to align with Paris Agreement climate goals.",
        "target": "Climate-concerned investors, ESG-mandated funds, institutional investors with divestment mandates.",
        "criteria": "XLE (energy sector) is hard-blocked. Energy exposure >15% is RED; >30% is YELLOW warning.",
        "roadmap": "Commercial: MSCI Low Carbon Target Index, TCFD-aligned temperature scoring, Paris-Aligned Investment benchmarks.",
    },
    "geopolitical_screen": {
        "concept": "Excludes exposure to sanctioned and monitored countries based on US OFAC sanctions and geopolitical risk indicators.",
        "target": "Institutional investors, ESG-mandated funds, family offices avoiding authoritarian-regime exposure.",
        "criteria": "Hard: Russia, North Korea, Iran, Cuba, Syria, Myanmar (zero tolerance). Soft: China, Hong Kong, Taiwan, Saudi Arabia, UAE, Venezuela (threshold-adjustable warnings).",
        "roadmap": "Commercial: MSCI Country Risk Index integration, live OFAC SDN list API, FTSE Russell Geopolitical Risk Index.",
    },
    "low_volatility": {
        "concept": "Targets income-oriented and defensive investors who prioritize stable, predictable returns over high-growth exposure.",
        "target": "Retirees, risk-averse investors, capital preservation portfolios, target-date funds.",
        "criteria": "ETFs with 252-day volatility ≤15% pass. AGG, BND, LQD, SCHD, VIG, VOO, VTI are typical GREENs.",
        "roadmap": "Commercial: Rolling 60-day volatility, CVaR (Conditional Value at Risk), maximum drawdown-based filters.",
    },
    "high_dividend": {
        "concept": "Screens for income-generating ETFs with dividend yield ≥3%, filtering out low-yield growth ETFs.",
        "target": "Income-focused investors, dividend growth portfolios, yield-seeking retirees.",
        "criteria": "AGG, BND, LQD, TLT, SCHD, EFA are typical GREENs. SPY, QQQ, VTI are RED due to low yield.",
        "roadmap": "Commercial: Dividend growth rate, franked/unfranked yield adjustment, franked credit integration for international ETFs.",
    },
    "cost_conscious": {
        "concept": "Minimizes the drag of management fees on long-term returns by filtering for expense ratios ≤0.10%.",
        "target": "Long-term investors, passive investors, fee-sensitive index fund buyers.",
        "criteria": "ETFs with expense ratio ≤0.001 (10bps) pass. Most Vanguard and iShares broad-market ETFs qualify. QQQ, EEM, GLD typically fail.",
        "roadmap": "Commercial: Transaction cost analysis (TCA), bid-ask spread scoring, fiscal year average vs. reported expense ratio.",
    },
    "tech_heavy": {
        "concept": "Concentrates exposure in technology-forward US equity ETFs, targeting investors who believe tech will outperform.",
        "target": "Growth investors, thematic investors, investors bullish on AI/semiconductor trends.",
        "criteria": "QQQ (Nasdaq 100), XLK (tech sector), VTI/VOO/SPY (broad US equity, all tech-heavy). Green if in the tech-heavy universe.",
        "roadmap": "Commercial: FactSet Ownership Tags, GICS technology sub-industry breakdown, AI exposure scoring.",
    },
    "tech_free": {
        "concept": "The inverse of Tech-Heavy — removes technology exposure for investors who want broad market exposure without tech sector concentration.",
        "target": "Diversified investors, ESG investors concerned about tech monopolies, value investors.",
        "criteria": "AGG, BND, SCHD, XLE, XLF, XLV, GLD, SLV, EEM, EFA, VEA, VWO pass. QQQ, XLK, VTI, VOO, SPY are excluded.",
        "roadmap": "Commercial: GICS sector breakdown, AI/cryptocurrency exposure flags, FANG+ exclusion overlays.",
    },
    "core_satellite": {
        "concept": "Ensures a dominant core of US broad-market equity with satellite positions in international and alternative assets.",
        "target": "Strategic asset allocators, fiduciary investors, model portfolio builders.",
        "criteria": "Portfolio-level check: ≥60% of portfolio must be in US Broad Equity (Cluster 1). If below, entire portfolio gets a YELLOW warning.",
        "roadmap": "Commercial: Custom benchmark construction, Glide Path analysis, liability-driven investing (LDI) integration.",
    },
    "esg_screen": {
        "concept": "Uses cosine similarity to ESGU (iShares MSCI USA ESG Select ETF) in 9-dimensional feature space as a free ESG proxy. MSCI ESG scores require a paid API.",
        "target": "ESG-motivated investors without budget for MSCI/Sustainalytics data. Beta users of the Argus platform.",
        "criteria": "Cosine similarity ≥0.80 to ESGU = GREEN. 0.60–0.80 = YELLOW. <0.60 = RED. VTI/VOO score ~0.998 to ESGU (US equity alignment). Energy (XLE) scores −0.46.",
        "roadmap": "Commercial: MSCI ESG API, Sustainalytics Risk Ratings, SDG Impact Mapping via MSCI SDG Framework. Roadmap note: SDG alignment already referenced in preset description via MSCI SDG Impact Framework.",
    },
}

# Precompute standardized features for cosine similarity
_scaler = StandardScaler()
_X9_scaled = _scaler.fit_transform(_features9.values)


# ── Compliance Engine ───────────────────────────────────────────────────────────


def check_etf_compliance(
    ticker: str,
    preset_id: str,
    constraint_overrides: dict | None = None,
) -> tuple[str, str]:
    """
    Returns (status, detail) where status ∈ {red, yellow, green}.

    Hard constraint → red (failing)
    Soft constraint → yellow (warning)
    No violation   → green

    constraint_overrides: dict keyed by constraint_id, each containing:
        - type: "hard" or "soft"  (for country/sector sliders)
        - threshold: 0-20 (slider value = max tolerable emerging market %)
        - For ethical categories: keyed by "cat_<category_id>", value = bool (enabled)
    """
    if preset_id == "none":
        return "green", "No screening active"

    preset = _presets["presets"].get(preset_id, {})
    constraints = preset.get("constraints", {})
    hard = dict(constraints.get("hard", {}))
    soft = dict(constraints.get("soft", {}))
    impl = preset.get("_impl", {})
    flags = impl.get("flagged_etfs", {})
    categories = impl.get("categories", {})
    sector_blacklist = list(hard.get("sector_blacklist", []))
    sector_soft_blacklist = list(soft.get("sector_blacklist", []))
    overrides = constraint_overrides or {}

    if ticker in sector_blacklist:
        reason = impl.get("sector_blacklist", {}).get(ticker, "Blacklisted sector")
        return "red", f"HARD: {reason}"

    if ticker in sector_soft_blacklist:
        reason = impl.get("sector_blacklist", {}).get(ticker, "Soft blacklisted")
        return "yellow", f"SOFT: {reason}"

    # Country exposure: may be overridden by constraint threshold slider
    # Override threshold is "max tolerable emerging market %" (slider 0-20)
    # Internal model uses "min US/allied exposure" = 1 - threshold/100
    country_override = overrides.get("country_exposure", {})
    raw_vals = _raw_feats.loc[ticker] if ticker in _raw_feats.index else pd.Series({})
    country_exp = float(raw_vals.get("country_exposure", 0.5))

    if country_override:
        # User-set threshold: convert slider % to min US exposure
        threshold_pct = country_override.get("threshold", 0)
        const_type = country_override.get("type", "hard")
        min_us = 1.0 - threshold_pct / 100.0
        violation = country_exp < min_us
        if violation:
            exposure_pct = int(round((1 - country_exp) * 100))
            detail = f"{const_type.upper()}: {exposure_pct}% emerging > {threshold_pct}% max"
            return "red" if const_type == "hard" else "yellow", detail
    else:
        # Default preset behavior: flagged ETFs + country_exposure.min
        if ticker in flags:
            return "red", f"HARD: {flags[ticker]}"

        country_hard = hard.get("country_exposure", {})
        country_soft = soft.get("country_exposure", {})
        if "min" in country_hard and country_exp < country_hard["min"]:
            return "red", f"HARD: country_exposure={country_exp:.2f} < min={country_hard['min']}"
        if "min" in country_soft and country_exp < country_soft["min"]:
            return "yellow", f"SOFT: country_exposure={country_exp:.2f} < min={country_soft['min']}"

    # ── Per-country checks (geopolitical_screen preset) ─────────────────────────────
    hard_countries = impl.get("hard_countries", {})
    soft_countries = impl.get("soft_countries", {})

    # Build country overrides dict from the active preset's overrides
    preset_override_keys = overrides.get(preset_id, {})
    country_overrides = {
        k: v
        for k, v in preset_override_keys.items()
        if not k.startswith("cat_")
        and k not in ("country_exposure",)
        and (k.startswith("hard_") or k.startswith("soft_"))
    }

    # Hard countries
    for country_id, cdef in hard_countries.items():
        key = f"hard_{country_id}"
        if country_overrides:
            override = country_overrides.get(key, {})
            enabled = override.get("enabled", cdef.get("default", False))
        else:
            enabled = cdef.get("default", False)
        if not enabled:
            continue
        affected = cdef.get("affected_etfs", [])
        if ticker not in affected:
            continue
        label = cdef.get("label", country_id.title())
        return "red", f"HARD: {label} exposure"

    # Soft countries
    for country_id, cdef in soft_countries.items():
        key = f"soft_{country_id}"
        if country_overrides:
            override = country_overrides.get(key, {})
            enabled = override.get("enabled", cdef.get("default", False))
            threshold = override.get("threshold", cdef.get("threshold", 10.0))
        else:
            enabled = cdef.get("default", False)
            threshold = cdef.get("threshold", 10.0)
        if not enabled:
            continue
        affected = cdef.get("affected_etfs", [])
        if ticker not in affected:
            continue
        # emerging_pct = % non-US exposure for this ticker
        emerging_pct = (1.0 - country_exp) * 100.0
        if emerging_pct > threshold:
            label = cdef.get("label", country_id.title())
            return "yellow", f"SOFT: {label} {emerging_pct:.0f}% > {threshold:.0f}% max"

    # ── Ethical categories (ethical_investor preset) ─────────────────────────────
    if categories:
        cat_overrides = {
            k.replace("cat_", ""): v for k, v in overrides.items() if k.startswith("cat_")
        }
        for cat_id, cat_def in categories.items():
            # Determine if this category is active
            if cat_overrides:
                enabled = cat_overrides.get(cat_id, {}).get(
                    "enabled", cat_def.get("default", False)
                )
            else:
                enabled = cat_def.get("default", False)

            if not enabled:
                continue

            affected = cat_def.get("affected_etfs", [])
            if ticker not in affected:
                continue

            is_hard = cat_def.get("hard", False)
            label = cat_def.get("label", cat_id.title())
            note = cat_def.get("note", "")

            if affected == [] and note:
                # Adult content — informational note only, no flagging
                return "green", "Compliant"

            detail = f"{label}"
            if note:
                detail += f": {note}"
            return ("red", f"HARD: {detail}") if is_hard else ("yellow", f"SOFT: {detail}")

    # ── Feature threshold rule (Low Volatility, High Dividend, Cost-Conscious) ───────
    rule_type = impl.get("rule_type")
    if rule_type == "feature_threshold":
        feature = impl.get("feature")
        operator = impl.get("operator", "<=")
        threshold = impl.get("threshold", 0.0)
        green_label = impl.get("green_label", "Compliant")
        red_label = impl.get("red_label", "Non-compliant")

        if ticker in _raw_feats.index:
            value = float(_raw_feats.loc[ticker, feature])
            passed = (operator == "<=" and value <= threshold) or (
                operator == ">=" and value >= threshold
            )
            if passed:
                return "green", green_label
            else:
                return "red", f"{red_label}"
        else:
            return "green", "Compliant"

    # ── Ticker list rule (Tech-Heavy, Tech-Free) ───────────────────────────────────
    if rule_type == "ticker_list":
        green_etfs = impl.get("green_etfs", [])
        red_etfs = impl.get("red_etfs", [])
        yellow_etfs = impl.get("yellow_etfs", [])
        green_label = impl.get("green_label", "Compliant")
        red_label = impl.get("red_label", "Non-compliant")

        if ticker in green_etfs:
            return "green", green_label
        elif ticker in red_etfs:
            return "red", red_label
        elif ticker in yellow_etfs:
            return "yellow", "Warning"
        else:
            return "green", green_label

    # ── Similarity benchmark rule (ESG Screen) ─────────────────────────────────────
    if rule_type == "similarity_benchmark":
        benchmark = impl.get("benchmark_ticker", "ESGU")
        thresh_green = impl.get("threshold_green", 0.80)
        thresh_yellow = impl.get("threshold_yellow", 0.60)
        green_label = impl.get("green_label", "ESG-aligned")
        yellow_label = impl.get("yellow_label", "Moderate ESG alignment")
        red_label = impl.get("red_label", "Low ESG alignment")

        if ticker not in _universe.index or benchmark not in _universe.index:
            return "green", green_label

        benchmark_vec = _X9_scaled[_universe.index.get_loc(benchmark)].reshape(1, -1)
        ticker_vec = _X9_scaled[_universe.index.get_loc(ticker)].reshape(1, -1)
        sim = cosine_similarity(benchmark_vec, ticker_vec)[0][0]

        if sim >= thresh_green:
            return "green", f"{green_label} (sim={sim:.2f})"
        elif sim >= thresh_yellow:
            return "yellow", f"{yellow_label} (sim={sim:.2f})"
        else:
            return "red", f"{red_label} (sim={sim:.2f})"

    return "green", "Compliant"


def compute_portfolio_compliance(
    tickers: list,
    preset_id: str,
    constraint_overrides: dict | None = None,
) -> dict[str, dict]:
    """Compute compliance for each position in portfolio (handles both str and dict entries)."""
    results = {}
    # Normalize to ticker strings
    ticker_list = []
    for entry in tickers:
        if isinstance(entry, dict):
            ticker_list.append(entry.get("ticker", ""))
        else:
            ticker_list.append(str(entry))

    preset = _presets["presets"].get(preset_id, {})
    impl = preset.get("_impl", {})
    rule_type = impl.get("rule_type")

    # Portfolio-level rule: Core-Satellite
    if rule_type == "portfolio_level":
        cluster_id = impl.get("cluster_id")
        threshold = impl.get("threshold", 0.60)
        green_label = impl.get("green_label", "Portfolio balanced")
        yellow_detail = impl.get("yellow_detail", "Core <60%")

        if not ticker_list:
            return {}

        cluster_count = sum(1 for t in ticker_list if get_cluster(t) == cluster_id)
        cluster_pct = cluster_count / len(ticker_list)

        if cluster_pct >= threshold:
            portfolio_status = "green"
            portfolio_detail = green_label
        else:
            portfolio_status = "yellow"
            portfolio_detail = (
                f"{yellow_detail} ({cluster_count}/{len(ticker_list)} = {cluster_pct:.0%})"
            )

        for t in ticker_list:
            results[t] = {"status": portfolio_status, "detail": portfolio_detail}
        return results

    # Standard per-ETF compliance
    for t in ticker_list:
        status, detail = check_etf_compliance(t, preset_id, constraint_overrides)
        results[t] = {"status": status, "detail": detail}
    return results


def compliance_score(
    tickers: list,
    preset_id: str,
    constraint_overrides: dict | None = None,
) -> tuple[float, float, int, int]:
    """Returns (value_weighted_score, count_score, green_count, total_count)."""
    if not tickers:
        return (100.0, 100.0, 0, 0)
    results = compute_portfolio_compliance(tickers, preset_id, constraint_overrides)

    # Build market value lookup
    total_value = 0.0
    green_value = 0.0
    green_count = 0
    total_count = 0

    for entry in tickers:
        if isinstance(entry, dict):
            tkr = entry.get("ticker", "")
            mv = entry.get("market_value", 0.0)
        else:
            tkr = str(entry)
            mv = 0.0

        if tkr not in results:
            continue
        status = results[tkr]["status"]
        total_count += 1
        if status == "green":
            green_count += 1
        if mv > 0:
            total_value += mv
            if status == "green":
                green_value += mv

    # Count-based score (0-100)
    count_score = (green_count / total_count * 100) if total_count > 0 else 100.0

    # Value-weighted score (0-100) — weights by market value
    value_score = (green_value / total_value * 100) if total_value > 0 else 100.0

    return (round(value_score, 1), round(count_score, 1), green_count, total_count)


# ── Recommendation Engine ───────────────────────────────────────────────────────


def get_cluster(ticker: str) -> int:
    return _cluster_labels.get(ticker, -1)


def cosine_sim_in_cluster(ticker: str, top_n: int = 3) -> list[dict]:
    """Return top-N similar ETFs within the same cluster (cosine similarity)."""
    if ticker not in _features9.index:
        return []
    idx = list(_features9.index).index(ticker)
    cluster = _cluster_labels[ticker]

    tickers = list(_features9.index)
    same_cluster_idx = [
        i for i, t in enumerate(tickers) if t != ticker and _cluster_labels.get(t) == cluster
    ]
    if not same_cluster_idx:
        return []

    sims = cosine_similarity(_X9_scaled[idx : idx + 1], _X9_scaled[same_cluster_idx])[0]
    peer_tickers = [tickers[i] for i in same_cluster_idx]

    ranked = sorted(zip(peer_tickers, sims, strict=True), key=lambda x: x[1], reverse=True)[:top_n]

    out = []
    query_feats = _raw_feats.loc[ticker] if ticker in _raw_feats.index else None
    for peer_t, sim in ranked:
        if peer_t not in _raw_feats.index:
            continue
        peer_feats = _raw_feats.loc[peer_t]
        diffs = []
        if query_feats is not None:
            for col in ["expense_ratio", "yield", "volatility_252d"]:
                qv = float(query_feats.get(col, 0))
                pv = float(peer_feats.get(col, 0))
                if abs(qv - pv) > 0.01:
                    diffs.append(f"{col}: {qv:.3f} vs {pv:.3f}")
        cluster_name = CLUSTER_NAMES.get(cluster, f"Cluster {cluster}")
        out.append(
            {
                "ticker": peer_t,
                "name": _universe.loc[peer_t, "name"] if peer_t in _universe.index else peer_t,
                "cluster": cluster_name,
                "cosine_similarity": round(float(sim), 4),
                "key_difference": "; ".join(diffs[:2]) if diffs else "Similar profile",
            }
        )
    return out


# ── App Layout ─────────────────────────────────────────────────────────────────

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Argus — ETF Compliance & Recommendation",
    suppress_callback_exceptions=True,
)
app.layout = dbc.Container(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="store-portfolio", data=[]),
        dcc.Store(id="store-preset", data="none"),
        dcc.Store(id="store-constraint-overrides", data={}),
        dcc.Store(id="store-feedback", data=[]),
        dcc.Store(id="store-holdings-visible", data={}),
        dcc.Store(id="store-import", data={"positions": [], "imported": False, "log": ""}),
        dbc.Row(
            dbc.Col(
                html.H2(
                    "Argus ETF Compliance Dashboard",
                    style={"margin": "12px 0 6px"},
                ),
                width="auto",
            ),
        ),
        dbc.Row(
            dbc.Col(
                dbc.ButtonGroup(
                    [
                        dbc.Button(
                            "1. Compliance Editor", id="btn-page-1", outline=True, active=True
                        ),
                        dbc.Button("2. xray_map", id="btn-page-2", outline=True),
                        dbc.Button("3. Recommend", id="btn-page-3", outline=True),
                    ],
                    id="nav-buttons",
                ),
                style={"marginBottom": 16},
            ),
        ),
        # Below tabs: two-column layout
        dbc.Row(
            [
                dbc.Col(
                    html.Div(id="preset-panel"),
                    width=5,
                    style={"borderRight": "1px solid #eee", "paddingRight": 16},
                ),
                dbc.Col(
                    [
                        html.Div(id="portfolio-panel", style={"marginBottom": 12}),
                        html.Div(id="constraint-panel", style={"marginBottom": 12}),
                    ],
                    width=7,
                ),
            ]
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="page-content"),
                width=12,
            ),
        ),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


# ── PAGE 1: Compliance Editor ──────────────────────────────────────────────────


def page1_layout(
    active_preset: str = "none",
    portfolio: list | None = None,
    constraint_overrides: dict | None = None,
) -> html.Div:
    """Returns the right column content (score + table) - left sidebar is separate."""
    portfolio = portfolio or []
    constraint_overrides = constraint_overrides or {}

    if portfolio:
        overrides = constraint_overrides.get(active_preset, {})
        comp = compute_portfolio_compliance(portfolio, active_preset, overrides)
        value_score, count_score, green_count, total_count = compliance_score(
            portfolio, active_preset, overrides
        )
        score_color = (
            "success" if value_score >= 80 else "warning" if value_score >= 50 else "danger"
        )

        # Build lookup for market values from portfolio entries (handle both str and dict)
        market_values: dict[str, float] = {}
        quantities: dict[str, float] = {}
        total_mv = 0.0
        for entry in portfolio:
            if isinstance(entry, dict):
                tkr = entry.get("ticker", "")
                qty = entry.get("quantity", 0)
                mv = entry.get("market_value", 0)
            else:
                tkr = str(entry)
                qty = 0
                mv = 0
            quantities[tkr] = qty
            if mv > 0:
                market_values[tkr] = mv
                total_mv += mv

        rows = []
        for entry in portfolio:
            if isinstance(entry, dict):
                tkr = entry.get("ticker", "")
                qty = entry.get("quantity", 0)
                mv = entry.get("market_value", 0)
            else:
                tkr = str(entry)
                qty = 0
                mv = market_values.get(tkr, 0)
            st = comp[tkr]["status"]
            color_map = {"green": "#d4edda", "yellow": "#fff3cd", "red": "#f8d7da"}
            bg = color_map.get(st, "#f8f9fa")

            # Weight
            weight = (mv / total_mv * 100) if total_mv > 0 else 0

            # X-ray detail panel (collapsible via <details>/<summary>)
            xray_panel = _build_xray_panel(tkr)

            # Row: summary line + expandable detail
            rows.append(
                html.Tr(
                    [
                        html.Td(
                            html.Details(
                                [
                                    html.Summary(
                                        [
                                            html.Strong(tkr),
                                            "  ",
                                            html.Small(
                                                (
                                                    _universe.loc[tkr, "name"]
                                                    if tkr in _universe.index
                                                    else tkr
                                                ),
                                                style={"color": "#666"},
                                            ),
                                        ],
                                        style={"cursor": "pointer", "list-style": "none"},
                                    ),
                                    html.Div(xray_panel, style={"padding": "8px 0"}),
                                ],
                                open=False,
                            ),
                            style={"background": bg},
                        ),
                        html.Td(
                            str(int(qty)) if qty else "—",
                            style={"background": bg, "textAlign": "right"},
                        ),
                        html.Td(
                            f"${mv:,.0f}" if mv else "—",
                            style={"background": bg, "textAlign": "right"},
                        ),
                        html.Td(
                            f"{weight:.1f}%" if total_mv > 0 else "—",
                            style={"background": bg, "textAlign": "right"},
                        ),
                        html.Td(CLUSTER_NAMES.get(get_cluster(tkr), "—"), style={"background": bg}),
                        html.Td(
                            dbc.Badge(
                                st.upper(),
                                color={"green": "success", "yellow": "warning", "red": "danger"}[
                                    st
                                ],
                            ),
                            style={"background": bg},
                        ),
                        html.Td(html.Small(comp[tkr]["detail"]), style={"background": bg}),
                        html.Td(
                            dbc.Button(
                                "×",
                                id={"type": "remove-btn", "index": tkr},
                                size="sm",
                                color="link",
                                style={"padding": "0 4px", "fontSize": "14px", "lineHeight": "1"},
                            ),
                            style={"background": bg, "textAlign": "center"},
                        ),
                    ],
                )
            )

        compliance_table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("ETF", style={"width": "12%"}),
                            html.Th("Qty", style={"width": "6%"}),
                            html.Th("Mkt Value", style={"width": "9%"}),
                            html.Th("Weight", style={"width": "7%"}),
                            html.Th("Cluster", style={"width": "11%"}),
                            html.Th("Status", style={"width": "7%"}),
                            html.Th("Detail", style={"width": "38%"}),
                            html.Th("Rm.", style={"width": "10%"}),
                        ]
                    )
                ),
                html.Tbody(rows),
            ],
            bordered=True,
            hover=True,
            style={"fontSize": "13px"},
        )
        score_card = dbc.Card(
            dbc.CardBody(
                [
                    html.H4(f"Compliance Score: {value_score}%", className=f"text-{score_color}"),
                    dbc.Progress(value=value_score, color=score_color, style={"height": "8px"}),
                    html.P(
                        f"Compliant ETFs: {green_count} of {total_count} ({count_score}% by count)",
                        style={"margin": "4px 0 0", "fontSize": "12px", "color": "#666"},
                    ),
                ]
            ),
            style={"marginBottom": 16},
        )
    else:
        compliance_table = html.P(
            "Add ETFs to your portfolio to see compliance + X-ray details.",
            style={"color": "#888"},
        )
        score_card = html.Div()

    # Return only the right column (left sidebar is now separate in app.layout)
    return dbc.Col(
        [
            score_card,
            compliance_table,
        ],
        width=8,
    )


# ── PAGE 2: UMAP xray_map ──────────────────────────────────────────────────────


def page2_layout(portfolio: list | None = None, preset_id: str = "none") -> html.Div:
    portfolio = portfolio or []

    # Build scatter trace
    coords_df = _umap_coords.copy()
    coords_df["cluster_label"] = coords_df["cluster"].map(
        lambda c: CLUSTER_NAMES.get(int(c), f"Cluster {c}")
    )

    # Color by cluster
    color_discrete_map = {
        CLUSTER_NAMES[0]: "#e41a1c",
        CLUSTER_NAMES[1]: "#377eb8",
        CLUSTER_NAMES[2]: "#ff7f00",
        CLUSTER_NAMES[3]: "#4daf4a",
        CLUSTER_NAMES[4]: "#984ea3",
    }

    comp = compute_portfolio_compliance(portfolio, preset_id) if portfolio else {}

    # Build ticker set from portfolio (handle both str and dict entries)
    portfolio_tickers = set()
    for entry in portfolio:
        if isinstance(entry, dict):
            portfolio_tickers.add(entry.get("ticker", ""))
        else:
            portfolio_tickers.add(str(entry))

    # coords_df: ticker is the index (from index_col=0 in read_csv)
    coords_df = coords_df.reset_index(names="ticker")

    # Determine marker colors and symbols
    marker_colors = []
    marker_sizes = []
    hover_texts = []
    for _, row in coords_df.iterrows():
        t = row["ticker"]
        if t in portfolio_tickers:
            status = comp.get(t, {}).get("status", "green")
            if status == "red":
                marker_colors.append("#dc3545")
                marker_sizes.append(20)
            elif status == "yellow":
                marker_colors.append("#ffc107")
                marker_sizes.append(18)
            else:
                marker_colors.append("#198754")
                marker_sizes.append(16)
            hover_texts.append(f"{t}: {status.upper()} — {comp[t]['detail']}")
        else:
            marker_colors.append(color_discrete_map.get(row["cluster_label"], "#999"))
            marker_sizes.append(10)
            hover_texts.append(f"{t}<br>{row['cluster_label']}")

    coords_df["marker_color"] = marker_colors
    coords_df["marker_size"] = marker_sizes
    coords_df["hover_text"] = hover_texts

    fig = go.Figure()

    # Plot by cluster
    for cluster_name, color in color_discrete_map.items():
        sub = coords_df[coords_df["cluster_label"] == cluster_name]
        # Check if any in portfolio
        in_portfolio = sub["ticker"].isin(portfolio_tickers)
        if in_portfolio.any():
            # Plot non-portfolio first, then portfolio on top
            non_port = sub[~in_portfolio]
            port = sub[in_portfolio]
            fig.add_trace(
                go.Scatter(
                    x=non_port["umap_x"],
                    y=non_port["umap_y"],
                    mode="markers+text",
                    marker=dict(size=non_port["marker_size"], color=color, opacity=0.7),
                    text=non_port["ticker"],
                    textposition="top center",
                    textfont=dict(size=9),
                    hoverinfo="text",
                    hovertext=non_port["hover_text"],
                    name=cluster_name,
                    showlegend=True,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=port["umap_x"],
                    y=port["umap_y"],
                    mode="markers+text",
                    marker=dict(
                        size=port["marker_size"],
                        color=port["marker_color"],
                        symbol="diamond",
                        line=dict(color="white", width=2),
                    ),
                    text=port["ticker"],
                    textposition="top center",
                    textfont=dict(size=11, color="black"),
                    hoverinfo="text",
                    hovertext=port["hover_text"],
                    name=f"{cluster_name} (portfolio)",
                    showlegend=False,
                )
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=sub["umap_x"],
                    y=sub["umap_y"],
                    mode="markers+text",
                    marker=dict(size=sub["marker_size"], color=color, opacity=0.7),
                    text=sub["ticker"],
                    textposition="top center",
                    textfont=dict(size=9),
                    hoverinfo="text",
                    hovertext=sub["hover_text"],
                    name=cluster_name,
                    showlegend=True,
                )
            )

    fig.update_layout(
        title=dict(text="ETF Universe — UMAP 2D (K=5 clusters)", x=0.5),
        xaxis_title="UMAP 1",
        yaxis_title="UMAP 2",
        legend_title="Cluster",
        height=600,
        template="plotly_white",
    )

    return html.Div(
        [
            dbc.Row(
                dbc.Col(
                    [
                        html.H5("UMAP xray_map — Portfolio Highlighted"),
                        html.P(
                            "Diamonds = your portfolio (red=violation, yellow=warning, green=compliant) "
                            "| Circles = universe ETFs colored by cluster",
                            style={"fontSize": 12, "color": "#666"},
                        ),
                        dcc.Graph(figure=fig, style={"height": "65vh"}),
                    ]
                )
            ),
            # ETF detail panel
            dbc.Row(
                dbc.Col(
                    html.Div(id="etf-detail-panel", style={"marginTop": 16}),
                    width=6,
                )
            ),
        ]
    )


# ── PAGE 3: Recommend ─────────────────────────────────────────────────────────


def page3_layout(
    portfolio: list | None = None,
    preset_id: str = "none",
    constraint_overrides: dict | None = None,
) -> html.Div:
    portfolio = portfolio or []
    constraint_overrides = constraint_overrides or {}
    if not portfolio:
        return html.Div(
            dbc.Alert(
                "Add ETFs to your portfolio on the Compliance Editor page first.", color="info"
            )
        )

    overrides = constraint_overrides.get(preset_id, {})
    comp = compute_portfolio_compliance(portfolio, preset_id, overrides)

    # Build ticker -> market_value lookup and total portfolio value
    ticker_mv = {}
    total_mv = 0.0
    for entry in portfolio:
        if isinstance(entry, dict):
            tkr = entry.get("ticker", "")
            mv = entry.get("market_value", 0.0)
        else:
            tkr = str(entry)
            mv = 0.0
        ticker_mv[tkr] = mv
        total_mv += mv

    # Normalize violating tickers (handle both str and dict entries)
    violating_tickers = []
    for entry in portfolio:
        tkr = entry.get("ticker", "") if isinstance(entry, dict) else str(entry)
        if comp[tkr]["status"] in ("red", "yellow"):
            violating_tickers.append(tkr)

    if not violating_tickers:
        return html.Div(
            dbc.Alert(
                [
                    html.H5("Portfolio is fully compliant! 🎉"),
                    html.P("No violations found. No replacements needed."),
                ],
                color="success",
            )
        )

    cards = []
    for ticker in violating_tickers:
        status = comp[ticker]["status"]
        cluster_id = get_cluster(ticker)
        cluster_name = CLUSTER_NAMES.get(cluster_id, f"Cluster {cluster_id}")
        recs = cosine_sim_in_cluster(ticker, top_n=3)
        mv = ticker_mv.get(ticker, 0)
        weight_pct = (mv / total_mv * 100) if total_mv > 0 else 0

        rec_rows = []
        for rec in recs:
            rec_tkr = rec["ticker"]
            swap_value = (
                mv  # replacing violating with compliant removes this much violating exposure
            )
            swap_desc = (
                f"Replacing {ticker} with {rec_tkr} resolves SGD {swap_value:,.0f}"
                if swap_value > 0
                else ""
            )
            rec_rows.append(
                html.Tr(
                    [
                        html.Td(html.Strong(rec_tkr)),
                        html.Td(rec["name"]),
                        html.Td(rec["cluster"]),
                        html.Td(f"{rec['cosine_similarity']:.4f}"),
                        html.Td(html.Small(rec["key_difference"])),
                        (
                            html.Td(html.Small(swap_desc, style={"color": "#155724"}))
                            if swap_desc
                            else html.Td("")
                        ),
                    ]
                )
            )

        impact_desc = f"Impact: SGD {mv:,.0f} ({weight_pct:.1f}% of portfolio)" if mv > 0 else ""
        rec_table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th(h)
                            for h in [
                                "Ticker",
                                "Name",
                                "Cluster",
                                "Cosine Sim",
                                "Key Difference",
                                "Swap Effect",
                            ]
                        ]
                    )
                ),
                html.Tbody(rec_rows),
            ],
            bordered=True,
            size="sm",
        )

        cards.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.H5(
                                        [
                                            ticker,
                                            " — ",
                                            (
                                                _universe.loc[ticker, "name"]
                                                if ticker in _universe.index
                                                else ticker
                                            ),
                                        ]
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.Badge(
                                        f"VIOLATION: {comp[ticker]['detail']}",
                                        color="danger" if status == "red" else "warning",
                                    ),
                                    width="auto",
                                ),
                            ],
                            align="center",
                        ),
                        (
                            html.Small(impact_desc, style={"color": "#856404"})
                            if impact_desc
                            else html.Div()
                        ),
                        html.Hr(),
                        html.H6(f"Top 3 Alternatives (same cluster: {cluster_name})"),
                        rec_table,
                    ]
                ),
                style={"marginBottom": 12},
            )
        )

    return html.Div(
        [
            dbc.Row(
                dbc.Col(
                    [
                        html.H4("Violation → Replacement Recommendations"),
                        html.P(
                            f"{len(violating_tickers)} of {len(portfolio)} ETFs have constraint violations. "
                            "Below are the top-3 most similar ETFs in the same cluster, "
                            "ranked by cosine similarity in the original 9-feature space.",
                            style={"color": "#666"},
                        ),
                    ]
                )
            ),
            *cards,
        ]
    )


# ── Callbacks ──────────────────────────────────────────────────────────────────


# Portfolio store update: Add button and Clear button
@app.callback(
    Output("store-portfolio", "data"),
    Output("store-feedback", "data"),
    Input("add-ticker-btn", "n_clicks"),
    Input("clear-portfolio-btn", "n_clicks"),
    State("ticker-input", "value"),
    State("store-portfolio", "data"),
    prevent_initial_call=True,
)
def update_portfolio(add_clicks, clear_clicks, ticker_input, portfolio):
    ctx = callback_context
    if add_clicks is None and clear_clicks is None:
        return portfolio or [], []
    trigger_id = ctx.triggered[0]["prop_id"]
    new_port = list(portfolio or [])
    feedback = []
    if "clear-portfolio-btn" in trigger_id:
        new_port = []
    elif "add-ticker-btn" in trigger_id:
        # Support comma-separated tickers
        raw = (ticker_input or "").strip()
        if not raw:
            return new_port, []
        tickers = [t.strip().upper() for t in raw.split(",")]
        # Build set of tickers already in portfolio (handle both str and dict entries)
        existing = set()
        for p in new_port:
            if isinstance(p, dict):
                existing.add(p.get("ticker", ""))
            else:
                existing.add(str(p))
        for t in tickers:
            if not t:
                continue
            if t not in ALL_TICKERS:
                feedback.append(f"'{t}' is not in the ETF universe")
            elif t in existing:
                feedback.append(f"'{t}' is already in portfolio")
            else:
                new_port.append(t)
    return new_port, feedback


# Clear active preset when Clear All is clicked
@app.callback(
    Output("store-preset", "data", allow_duplicate=True),
    Output("store-import", "data", allow_duplicate=True),
    Input("clear-portfolio-btn", "n_clicks"),
    State("store-preset", "data"),
    prevent_initial_call=True,
)
def clear_preset_on_clear(clear_clicks, active_preset):
    if clear_clicks is None:
        return active_preset or "none", {"positions": [], "imported": False, "log": ""}
    return "none", {"positions": [], "imported": False, "log": ""}


# Preset buttons: one callback per preset (avoids Dash 4.x ALL-pattern issue)
def _make_preset_callback(preset_id: str):
    def preset_callback(n_clicks, active_preset):
        if n_clicks is None or n_clicks == 0:
            return active_preset or "none"
        new_preset = active_preset or "none"
        return preset_id if preset_id != new_preset else "none"

    return preset_callback


# Per-preset callback (Dash 4.x safe — avoids ALL pattern server-side crash)
for preset_id in list(_presets["presets"].keys()):
    app.callback(
        Output("store-preset", "data", allow_duplicate=True),
        Input({"type": "preset-btn", "index": preset_id}, "n_clicks"),
        State("store-preset", "data"),
        prevent_initial_call="initial_duplicate",
    )(_make_preset_callback(preset_id))


# Per-ticker remove callbacks (Dash 4.x safe — avoids ALL pattern server-side crash)
def _make_remove_callback(ticker: str):
    @app.callback(
        Output("store-portfolio", "data", allow_duplicate=True),
        Input({"type": "port-remove-btn", "index": ticker}, "n_clicks"),
        Input({"type": "remove-btn", "index": ticker}, "n_clicks"),
        State("store-portfolio", "data"),
        prevent_initial_call=True,
    )
    def remove_etf(p1, p2, portfolio):
        if p1 is None and p2 is None:
            return portfolio or []
        new_port = list(portfolio or [])
        if ticker in new_port:
            new_port.remove(ticker)
        return new_port

    return remove_etf


for _ticker in ALL_TICKERS:
    _make_remove_callback(_ticker)


@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("store-portfolio", "data"),
    Input("store-preset", "data"),
    Input("store-constraint-overrides", "data"),
)
def render_page(pathname, portfolio, active_preset, constraint_overrides):
    constraint_overrides = constraint_overrides or {}
    if pathname == "/xray_map":
        return page2_layout(portfolio=portfolio, preset_id=active_preset)
    elif pathname == "/recommend":
        return page3_layout(
            portfolio=portfolio,
            preset_id=active_preset,
            constraint_overrides=constraint_overrides,
        )
    else:
        return dbc.Row(
            page1_layout(
                active_preset=active_preset,
                portfolio=portfolio,
                constraint_overrides=constraint_overrides,
            )
        )


# Preset panel - left column
@app.callback(
    Output("preset-panel", "children"),
    Input("store-preset", "data"),
)
def render_preset_panel(active_preset):
    return _build_preset_panel(active_preset or "none")


# Portfolio panel - right column (import + portfolio entry)
@app.callback(
    Output("portfolio-panel", "children"),
    Input("store-portfolio", "data"),
    Input("store-feedback", "data"),
)
def render_portfolio_panel(portfolio, feedback):
    return _build_portfolio_panel(portfolio or [], feedback or [])


# ── Constraint Threshold Panel ─────────────────────────────────────────────────


def _get_constraint_rows(
    preset_id: str,
    constraint_overrides: dict,
    portfolio: list,
) -> list:
    """Build per-constraint UI rows for the active preset."""
    if preset_id == "none" or preset_id not in _presets["presets"]:
        return []

    preset = _presets["presets"][preset_id]
    constraints = preset.get("constraints", {})
    hard = constraints.get("hard", {})
    soft = constraints.get("soft", {})
    rows = []

    # ── Country exposure constraint ────────────────────────────────────────────
    country_hard = hard.get("country_exposure", {})
    country_soft = soft.get("country_exposure", {})
    if country_hard or country_soft:
        override = constraint_overrides.get("country_exposure", {})
        const_type = override.get("type", "hard" if country_hard else "soft")
        if override:
            threshold = override.get("threshold", 0.0)
        else:
            # Default: HARD → 0% (zero tolerance), SOFT → preset soft threshold
            threshold = (
                country_hard.get("min", 0.0) * 100
                if country_hard
                else country_soft.get("min", 0.0) * 100
            )

        # Current portfolio exposure: show max emerging market % across portfolio
        max_emerging = 0.0
        for t in portfolio:
            if t in _raw_feats.index:
                ce = float(_raw_feats.loc[t, "country_exposure"])
                emerging = (1 - ce) * 100
                if emerging > max_emerging:
                    max_emerging = emerging

        rows.append(
            _build_constraint_row(
                constraint_id="country_exposure",
                label="Max Emerging Market",
                const_type=const_type,
                threshold=threshold,
                exposure_pct=round(max_emerging, 1),
                portfolio=portfolio,
            )
        )

    # ── Sector exposure constraints ────────────────────────────────────────────
    sector_hard_max = hard.get("sector_exposure", {}).get("max", {})
    sector_soft_max = soft.get("sector_exposure", {}).get("max", {})
    all_sectors = set(list(sector_hard_max.keys()) + list(sector_soft_max.keys()))
    for sector in sorted(all_sectors):
        h_thresh = sector_hard_max.get(sector, 1.0)
        s_thresh = sector_soft_max.get(sector, 1.0)
        override = constraint_overrides.get(f"sector_exposure_{sector}", {})
        const_type = override.get("type", "hard" if sector in sector_hard_max else "soft")
        if override:
            threshold = override.get("threshold", 0.0)
        else:
            # Default: HARD → hard threshold, SOFT → soft threshold
            threshold = h_thresh * 100 if sector in sector_hard_max else s_thresh * 100

        max_sector = 0.0
        for t in portfolio:
            if t in _raw_feats.index:
                se = float(_raw_feats.loc[t, "sector_exposure"])
                if se > max_sector:
                    max_sector = se

        rows.append(
            _build_constraint_row(
                constraint_id=f"sector_exposure_{sector}",
                label=f"Max {sector.title()} Sector",
                const_type=const_type,
                threshold=threshold,
                exposure_pct=round(max_sector * 100, 1),
                portfolio=portfolio,
            )
        )

    return rows


def _build_constraint_row(
    constraint_id: str,
    label: str,
    const_type: str,
    threshold: float,
    exposure_pct: float,
    portfolio: list,
) -> html.Div:
    """Build a single constraint row: label | HARD/SOFT | slider | exposure."""
    is_hard = const_type == "hard"
    border_color = "#dc3545" if is_hard else "#ffc107"

    def _type_style(t):
        return {"fontWeight": "bold", "fontSize": "11px", "padding": "2px 8px"}

    type_buttons = [
        dbc.Button(
            "HARD",
            id={"type": "const-hard-btn", "index": constraint_id},
            color="danger" if const_type == "hard" else "secondary",
            size="sm",
            style=_type_style(const_type),
        ),
        dbc.Button(
            "SOFT",
            id={"type": "const-soft-btn", "index": constraint_id},
            color="warning" if const_type == "soft" else "secondary",
            size="sm",
            style=_type_style(const_type),
        ),
    ]

    return html.Div(
        [
            # Label row
            html.Div(
                [
                    html.Small(
                        label,
                        style={"fontWeight": "bold", "color": border_color},
                    ),
                    html.Small(
                        f"({exposure_pct}%)" if exposure_pct > 0 else "",
                        style={"color": "#666", "marginLeft": 4},
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": 2},
            ),
            # Controls row
            html.Div(
                [
                    # Type toggle
                    dbc.ButtonGroup(
                        type_buttons,
                        size="sm",
                        style={"flexShrink": 0},
                    ),
                    # Slider
                    html.Div(
                        dcc.Slider(
                            id={"type": "const-slider", "index": constraint_id},
                            min=0,
                            max=20,
                            step=1,
                            value=threshold,
                            marks={i: f"{i}%" for i in range(0, 21, 5)},
                            tooltip={"placement": "bottom", "always_visible": True},
                            className="constraint-slider",
                        ),
                        style={"flex": 1, "margin": "0 8px", "minWidth": 80},
                    ),
                    # Threshold value
                    html.Small(
                        f"{int(threshold)}%",
                        style={
                            "width": 28,
                            "textAlign": "center",
                            "flexShrink": 0,
                            "fontWeight": "bold",
                            "color": border_color,
                        },
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "gap": 4},
            ),
        ],
        style={
            "borderLeft": f"3px solid {border_color}",
            "paddingLeft": 8,
            "marginBottom": 10,
            "paddingBottom": 6,
            "borderBottom": "1px solid #eee",
        },
    )


def build_constraint_panel(
    active_preset: str,
    constraint_overrides: dict,
    portfolio: list,
) -> html.Div:
    """Full constraint threshold panel shown below preset buttons."""
    if active_preset == "none":
        return html.Div([])

    preset_data = _presets["presets"].get(active_preset, {})

    # Compute effective default thresholds for each constraint, then check if any
    # override differs from its default (the "(modified)" marker should only appear
    # when the user has actually changed a value away from the default)
    hard = preset_data.get("constraints", {}).get("hard", {})
    soft = preset_data.get("constraints", {}).get("soft", {})
    country_hard = hard.get("country_exposure", {})
    country_soft = soft.get("country_exposure", {})
    defaults = {}
    # country_exposure default
    if country_hard:
        defaults["country_exposure"] = country_hard.get("min", 0.0) * 100
    elif country_soft:
        defaults["country_exposure"] = country_soft.get("min", 0.0) * 100
    # sector defaults
    sector_hard_max = hard.get("sector_exposure", {}).get("max", {})
    sector_soft_max = soft.get("sector_exposure", {}).get("max", {})
    all_sectors = set(list(sector_hard_max.keys()) + list(sector_soft_max.keys()))
    for sector in all_sectors:
        key = f"sector_exposure_{sector}"
        if sector in sector_hard_max:
            defaults[key] = sector_hard_max[sector] * 100
        elif sector in sector_soft_max:
            defaults[key] = sector_soft_max[sector] * 100

    preset_overrides = constraint_overrides.get(active_preset, {})
    is_modified = False
    for const_id, override_val in preset_overrides.items():
        default_thresh = defaults.get(const_id, 0.0)
        if abs(override_val.get("threshold", default_thresh) - default_thresh) > 0.5:
            is_modified = True
            break
        # Also mark modified if type was explicitly toggled away from default
        default_type = (
            "hard"
            if const_id in sector_hard_max or const_id == "country_exposure" and country_hard
            else "soft"
        )
        if override_val.get("type", default_type) != default_type:
            is_modified = True
            break

    rows = _get_constraint_rows(active_preset, constraint_overrides, portfolio)
    cat_rows = _build_ethical_categories_panel(active_preset, constraint_overrides)
    country_rows = _build_geopolitical_countries_panel(active_preset, constraint_overrides)

    if not rows and not cat_rows and not country_rows:
        return html.Div([])

    children = []
    if rows:
        children.append(
            html.H6(
                [
                    "Constraint Thresholds",
                    (
                        html.Span(
                            " (modified)",
                            style={"color": "#666", "fontWeight": "normal", "fontStyle": "italic"},
                        )
                        if is_modified
                        else None
                    ),
                ],
                style={"marginTop": 8, "marginBottom": 6},
            )
        )
        children.append(html.Div(rows, style={"fontSize": 12}))

    if country_rows:
        if rows or cat_rows:
            children.append(html.Hr(style={"margin": "12px 0 8px"}))
        children.extend(country_rows)

    if cat_rows:
        children.append(html.Hr(style={"margin": "12px 0 8px"}))
        children.append(html.H6("Ethical Exclusions", style={"marginBottom": 8}))
        children.extend(cat_rows)

    return html.Div(children)


def _build_ethical_categories_panel(active_preset: str, constraint_overrides: dict) -> list:
    """Build toggle panel for ethical investor categories.

    Uses individual dbc.Button toggles per category to avoid dcc.Checklist
    pattern-matching callback issues in Dash 4.x.
    """
    if active_preset != "ethical_investor":
        return []
    preset = _presets["presets"].get(active_preset, {})
    categories = preset.get("_impl", {}).get("categories", {})
    if not categories:
        return []

    overrides = constraint_overrides.get(active_preset, {})
    rows = []

    for cat_id, cat_def in categories.items():
        label = cat_def.get("label", cat_id.title())
        is_hard = cat_def.get("hard", False)
        border_color = "#dc3545" if is_hard else "#ffc107"
        badge_color = "danger" if is_hard else "warning"
        affected = cat_def.get("affected_etfs", [])
        description = cat_def.get("description", "")
        note = cat_def.get("note", "")
        affected_str = ", ".join(affected) if affected else ""

        # Determine current enabled state
        cat_override = overrides.get(f"cat_{cat_id}", {})
        enabled = cat_override.get("enabled", cat_def.get("default", False))

        rows.append(
            html.Div(
                [
                    dbc.Button(
                        "ON" if enabled else "OFF",
                        id={"type": "cat-toggle", "index": cat_id},
                        size="sm",
                        color="success" if enabled else "secondary",
                        style={"marginRight": 8, "minWidth": "50px"},
                    ),
                    html.Div(
                        [
                            html.Strong(label, style={"color": border_color}),
                            dbc.Badge(
                                "HARD" if is_hard else "SOFT",
                                color=badge_color,
                                style={"marginLeft": 6, "fontSize": "10px"},
                            ),
                            html.Small(
                                f" — {description}" if description else "",
                                style={"color": "#666", "marginLeft": 4},
                            ),
                            html.Small(
                                f" → {affected_str}" if affected_str else "",
                                style={"color": "#999", "marginLeft": 4},
                            ),
                            html.Small(
                                f" ({note})" if note else "",
                                style={"color": "#888", "marginLeft": 4, "fontStyle": "italic"},
                            ),
                        ],
                        style={
                            "display": "inline-flex",
                            "alignItems": "center",
                            "flexWrap": "wrap",
                            "gap": "4px",
                        },
                    ),
                ],
                style={
                    "borderLeft": f"3px solid {border_color}",
                    "paddingLeft": 8,
                    "marginBottom": 8,
                },
            )
        )

    return rows


def _build_geopolitical_countries_panel(active_preset: str, constraint_overrides: dict) -> list:
    """Build HARD/SOFT country checkbox panels for geopolitical_screen preset."""
    if active_preset != "geopolitical_screen":
        return []
    preset = _presets["presets"].get(active_preset, {})
    hard_countries = preset.get("_impl", {}).get("hard_countries", {})
    soft_countries = preset.get("_impl", {}).get("soft_countries", {})
    if not hard_countries and not soft_countries:
        return []
    overrides = constraint_overrides.get(active_preset, {})

    rows = []

    # ── HARD section ──────────────────────────────────────────────────────────────
    if hard_countries:
        rows.append(
            html.H6(
                "Hard Constraints — Zero Tolerance",
                style={"color": "#dc3545", "marginTop": 4, "marginBottom": 6},
            )
        )
        for country_id, cdef in hard_countries.items():
            label = cdef.get("label", country_id.title())
            override = overrides.get(f"hard_{country_id}", {})
            enabled = override.get("enabled", cdef.get("default", False))
            rows.append(
                html.Div(
                    [
                        dbc.Checkbox(
                            id={"type": "hard-country-checkbox", "index": country_id},
                            value=bool(enabled),
                            className="mr-2",
                        ),
                        html.Strong(label, style={"color": "#dc3545"}),
                        dbc.Badge(
                            "HARD", color="danger", style={"marginLeft": 6, "fontSize": "10px"}
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "marginBottom": 4},
                )
            )

    # ── SOFT section ─────────────────────────────────────────────────────────────
    if soft_countries:
        rows.append(html.Hr(style={"margin": "8px 0 6px"}))
        rows.append(
            html.H6(
                "Soft Constraints — Warning Threshold",
                style={"color": "#ffc107", "marginTop": 4, "marginBottom": 6},
            )
        )
        for country_id, cdef in soft_countries.items():
            label = cdef.get("label", country_id.title())
            override = overrides.get(f"soft_{country_id}", {})
            enabled = override.get("enabled", cdef.get("default", False))
            threshold = override.get("threshold", cdef.get("threshold", 10.0))

            rows.append(
                html.Div(
                    [
                        dbc.Checkbox(
                            id={"type": "soft-country-checkbox", "index": country_id},
                            value=bool(enabled),
                            className="mr-2",
                        ),
                        html.Strong(label, style={"color": "#333"}),
                        dbc.Badge(
                            "SOFT", color="warning", style={"marginLeft": 6, "fontSize": "10px"}
                        ),
                        html.Div(
                            [
                                html.Label(
                                    f"Max: {threshold:.0f}%",
                                    id={
                                        "type": "soft-country-threshold-label",
                                        "index": country_id,
                                    },
                                    style={"fontSize": 11, "color": "#666", "marginLeft": 4},
                                ),
                                html.Div(
                                    dcc.Slider(
                                        id={"type": "soft-country-slider", "index": country_id},
                                        min=0,
                                        max=30,
                                        step=5,
                                        value=threshold,
                                        marks={0: "0%", 10: "10%", 20: "20%", 30: "30%"},
                                        tooltip={"placement": "bottom", "template": "%{value}%"},
                                    ),
                                    style={
                                        "width": 120,
                                        "display": "inline-block",
                                        "marginLeft": 8,
                                    },
                                ),
                            ],
                            style={"marginTop": 2, "marginLeft": 20},
                        ),
                    ],
                    style={"marginBottom": 6},
                )
            )

    return rows


@app.callback(
    Output("store-constraint-overrides", "data"),
    Input({"type": "const-slider", "index": ALL}, "value"),
    Input({"type": "const-hard-btn", "index": ALL}, "n_clicks"),
    Input({"type": "const-soft-btn", "index": ALL}, "n_clicks"),
    Input({"type": "cat-checkbox", "index": ALL}, "value"),
    Input({"type": "cat-toggle", "index": ALL}, "n_clicks"),
    Input({"type": "hard-country-checkbox", "index": ALL}, "value"),
    Input({"type": "soft-country-checkbox", "index": ALL}, "value"),
    Input({"type": "soft-country-slider", "index": ALL}, "value"),
    State("store-constraint-overrides", "data"),
    State("store-preset", "data"),
    prevent_initial_call="initial_duplicate",
)
def _update_constraint_override(
    slider_values,
    hard_btn_clicks,
    soft_btn_clicks,
    cat_checkbox_values,
    cat_toggle_clicks,
    hard_country_values,
    soft_country_values,
    soft_slider_values,
    overrides,
    active_preset,
):
    """Handle constraint slider, type toggle, and ethical category checkbox changes."""

    ctx = callback_context
    active_preset = active_preset or "none"

    # Initialize overrides for this preset
    if active_preset not in overrides:
        overrides = dict(overrides)
        overrides[active_preset] = {}

    # Determine which input triggered
    if not ctx.triggered:
        return overrides

    trigger = ctx.triggered[0]
    prop_id = trigger["prop_id"]

    # Parse the triggered prop_id to determine constraint_id and type
    # prop_id format: '{"index":"weapons","type":"cat-toggle"}.n_clicks' (JSON + .suffix)
    # or a dict (Dash 4.x)
    import json

    if isinstance(prop_id, dict):
        parsed = prop_id
    else:
        try:
            # Strip the .n_clicks (or similar) suffix before parsing JSON
            json_part = prop_id.split(".")[0] if "." in prop_id else prop_id
            parsed = json.loads(json_part)
        except (json.JSONDecodeError, TypeError):
            return overrides

    constraint_id = parsed.get("index")
    trigger_type = parsed.get("type")

    # Clone overrides to avoid mutation
    overrides = dict(overrides) if overrides else {}
    overrides[active_preset] = (
        dict(overrides.get(active_preset, {})) if overrides.get(active_preset) else {}
    )

    if trigger_type == "const-slider":
        # Slider changed — slider_values is a list ordered by ALL_CONSTRAINT_IDS
        # Find the index of constraint_id in the matched inputs
        try:
            const_idx = ALL_CONSTRAINT_IDS.index(constraint_id)
        except ValueError:
            return overrides
        if const_idx < len(slider_values) and slider_values[const_idx] is not None:
            threshold = float(slider_values[const_idx])
            current = dict(overrides[active_preset].get(constraint_id, {}))
            overrides[active_preset][constraint_id] = {
                "type": current.get("type", "hard"),
                "threshold": threshold,
            }
    elif trigger_type in ("const-hard-btn", "const-soft-btn"):
        # HARD or SOFT button clicked — set the type directly
        # Compute the rendered constraint list for the current preset:
        preset_data = _presets["presets"].get(active_preset, {})
        preset_hard = preset_data.get("constraints", {}).get("hard", {})
        preset_soft = preset_data.get("constraints", {}).get("soft", {})
        preset_const_ids = []
        # Country constraint first if present
        if preset_hard.get("country_exposure") or preset_soft.get("country_exposure"):
            preset_const_ids.append("country_exposure")
        # Then sector constraints
        sector_hard = preset_hard.get("sector_exposure", {}).get("max", {})
        sector_soft = preset_soft.get("sector_exposure", {}).get("max", {})
        for sector in sorted(set(list(sector_hard.keys()) + list(sector_soft.keys()))):
            preset_const_ids.append(f"sector_exposure_{sector}")
        # Find position of constraint_id in the rendered list
        if constraint_id not in preset_const_ids:
            return overrides
        btn_idx = preset_const_ids.index(constraint_id)
        if trigger_type == "const-hard-btn":
            if btn_idx < len(hard_btn_clicks) and hard_btn_clicks[btn_idx]:
                overrides[active_preset][constraint_id] = {"type": "hard"}
        else:
            if btn_idx < len(soft_btn_clicks) and soft_btn_clicks[btn_idx]:
                overrides[active_preset][constraint_id] = {"type": "soft"}
    elif trigger_type == "cat-checkbox":
        # Ethical category checklist changed — cat_checkbox_values is a list of
        # selected cat_ids (e.g. ["weapons", "fossil_fuels"]). Update each
        # category's enabled status by computing the diff from stored state.
        if cat_checkbox_values is None:
            return overrides
        preset = _presets["presets"].get(active_preset, {})
        cat_defs = preset.get("_impl", {}).get("categories", {})
        cat_ids = list(cat_defs.keys())
        # Previous enabled set from overrides
        prev_enabled = set()
        for cat_id in cat_ids:
            cat_override = overrides.get(active_preset, {}).get(f"cat_{cat_id}", {})
            if cat_override.get("enabled", cat_defs.get(cat_id, {}).get("default", False)):
                prev_enabled.add(cat_id)
        new_enabled = set(cat_checkbox_values)
        # Toggle each changed category
        for cat_id in cat_ids:
            was_enabled = cat_id in prev_enabled
            is_enabled = cat_id in new_enabled
            if was_enabled != is_enabled:
                overrides[active_preset][f"cat_{cat_id}"] = {"enabled": is_enabled}
    elif trigger_type == "hard-country-checkbox":
        # Hard country checkbox toggled
        # hard_country_values is a list ordered by ALL_HARD_COUNTRY_IDS
        if constraint_id in ALL_HARD_COUNTRY_IDS and hard_country_values is not None:
            idx = ALL_HARD_COUNTRY_IDS.index(constraint_id)
            if idx < len(hard_country_values):
                enabled = bool(hard_country_values[idx])
                overrides[active_preset][f"hard_{constraint_id}"] = {"enabled": enabled}
    elif trigger_type == "soft-country-checkbox":
        # Soft country checkbox toggled
        # soft_country_values is a list ordered by ALL_SOFT_COUNTRY_IDS
        if constraint_id in ALL_SOFT_COUNTRY_IDS and soft_country_values is not None:
            idx = ALL_SOFT_COUNTRY_IDS.index(constraint_id)
            if idx < len(soft_country_values):
                enabled = bool(soft_country_values[idx])
                overrides[active_preset][f"soft_{constraint_id}"] = {
                    "enabled": enabled,
                    "threshold": overrides[active_preset]
                    .get(f"soft_{constraint_id}", {})
                    .get("threshold", 10.0),
                }
    elif trigger_type == "soft-country-slider":
        # Soft country threshold slider changed
        # soft_slider_values is a list ordered by ALL_SOFT_COUNTRY_IDS
        if constraint_id in ALL_SOFT_COUNTRY_IDS and soft_slider_values is not None:
            idx = ALL_SOFT_COUNTRY_IDS.index(constraint_id)
            if idx < len(soft_slider_values) and soft_slider_values[idx] is not None:
                threshold = float(soft_slider_values[idx])
                existing = overrides[active_preset].get(f"soft_{constraint_id}", {})
                overrides[active_preset][f"soft_{constraint_id}"] = {
                    "enabled": existing.get("enabled", True),
                    "threshold": threshold,
                }
    elif trigger_type == "cat-toggle":
        # Toggle button clicked — flip the category's enabled state
        # Guard: n_clicks must be > 0 for THIS specific button to handle the case where
        # ALL cat-toggle callbacks fire on preset change (Dash recreates component tree)
        try:
            cat_idx = ALL_CAT_IDS.index(constraint_id)
        except ValueError:
            pass
        else:
            if cat_idx < len(cat_toggle_clicks) and cat_toggle_clicks[cat_idx]:
                preset = _presets["presets"].get(active_preset, {})
                cat_defs = preset.get("_impl", {}).get("categories", {})
                if constraint_id in cat_defs:
                    current = dict(overrides.get(active_preset, {}).get(f"cat_{constraint_id}", {}))
                    current_enabled = current.get(
                        "enabled", cat_defs.get(constraint_id, {}).get("default", False)
                    )
                    new_enabled = not current_enabled
                    overrides.setdefault(active_preset, {})[f"cat_{constraint_id}"] = {
                        "enabled": new_enabled
                    }

    return overrides


@app.callback(
    Output("constraint-panel", "children"),
    Input("store-preset", "data"),
    Input("store-constraint-overrides", "data"),
    Input("store-portfolio", "data"),
)
def _render_constraint_panel(active_preset, constraint_overrides, portfolio):
    """Render the constraint threshold panel."""
    return build_constraint_panel(
        active_preset or "none",
        constraint_overrides or {},
        portfolio or [],
    )


def _build_preset_panel(active_preset: str) -> html.Div:
    """Build the left column with Screen Presets and rationale."""
    CATEGORY_ORDER = [
        "Ethical & ESG",
        "Geopolitical",
        "Risk & Cost",
        "Sector Focus",
        "Portfolio Structure",
    ]
    preset_by_category: dict[str, list] = {cat: [] for cat in CATEGORY_ORDER}
    uncategorized = []
    for pid, pdata in _presets["presets"].items():
        is_active = pid == active_preset
        btn_color = "primary" if is_active else "outline-secondary"
        btn = dbc.Button(
            [
                html.Strong(pdata["name"]),
                html.Br(),
                html.Small(pdata["description"], style={"color": "#aaa"}),
            ],
            id={"type": "preset-btn", "index": pid},
            color=btn_color,
            style={"textAlign": "left", "height": "100%", "margin": "4px"},
        )
        cat = pdata.get("preset_category")
        if cat in preset_by_category:
            preset_by_category[cat].append(btn)
        else:
            uncategorized.append(btn)

    preset_sections = []
    for cat in CATEGORY_ORDER:
        btns = preset_by_category.get(cat, [])
        if not btns:
            continue
        preset_sections.append(
            html.Div(
                [
                    html.H6(
                        cat,
                        style={
                            "marginBottom": 4,
                            "marginTop": 8,
                            "fontSize": "11px",
                            "color": "#888",
                            "textTransform": "uppercase",
                        },
                    ),
                    html.Div(btns, style={"display": "flex", "flexWrap": "wrap", "gap": "2px"}),
                ]
            )
        )
    if uncategorized:
        preset_sections.append(
            html.Div(
                [
                    html.H6(
                        "Other",
                        style={
                            "marginBottom": 4,
                            "marginTop": 8,
                            "fontSize": "11px",
                            "color": "#888",
                        },
                    ),
                    html.Div(
                        uncategorized, style={"display": "flex", "flexWrap": "wrap", "gap": "2px"}
                    ),
                ]
            )
        )

    rationale_rows = []
    if active_preset != "none" and active_preset in PRESET_RATIONALE:
        rat = PRESET_RATIONALE[active_preset]
        rationale_rows = [
            html.Hr(),
            html.H6("Why This Preset?", style={"marginBottom": 6}),
            html.Div(
                [
                    html.Strong("Concept: ", style={"color": "#333"}),
                    html.Span(rat.get("concept", ""), style={"color": "#555", "fontSize": "12px"}),
                ],
                style={"marginBottom": 6},
            ),
            html.Div(
                [
                    html.Strong("Target: ", style={"color": "#333"}),
                    html.Span(rat.get("target", ""), style={"color": "#555", "fontSize": "12px"}),
                ],
                style={"marginBottom": 6},
            ),
            html.Div(
                [
                    html.Strong("Criteria: ", style={"color": "#333"}),
                    html.Span(rat.get("criteria", ""), style={"color": "#555", "fontSize": "12px"}),
                ],
                style={"marginBottom": 6},
            ),
            html.Div(
                [
                    html.Strong("Roadmap: ", style={"color": "#333"}),
                    html.Span(
                        rat.get("roadmap", ""),
                        style={"color": "#888", "fontSize": "11px", "fontStyle": "italic"},
                    ),
                ],
            ),
        ]
    elif active_preset != "none":
        rationale_rows = [
            html.Hr(),
            html.Small("No rationale available for this preset.", style={"color": "#aaa"}),
        ]

    return html.Div(
        [
            html.H5("Screen Presets"),
            html.Div(preset_sections, style={"display": "block"}),
            *rationale_rows,
        ]
    )


def _build_portfolio_panel(portfolio: list, feedback: list) -> html.Div:
    """Build the right column with Import and Your Portfolio."""
    portfolio_chips = []
    for t in portfolio:
        portfolio_chips.append(
            dbc.ButtonGroup(
                [
                    dbc.Button(t, size="sm", disabled=True, color="secondary"),
                    dbc.Button(
                        "×",
                        id={"type": "port-remove-btn", "index": t},
                        size="sm",
                        color="outline-secondary",
                        style={"padding": "0 6px"},
                    ),
                ],
                size="sm",
                style={"margin": "2px"},
            )
        )

    feedback_rows = []
    for msg in feedback:
        feedback_rows.append(
            dbc.Alert(
                msg,
                color="warning",
                dismissable=True,
                style={"fontSize": "12px", "padding": "4px 8px"},
            )
        )

    return html.Div(
        [
            html.H5("Import from Brokerage"),
            html.Small(
                "Compatible with Interactive Brokers Activity Statement (.csv). "
                "Other brokerages: export positions as CSV with Symbol, Quantity columns.",
                style={"color": "#666", "fontSize": "11px"},
            ),
            dcc.Upload(
                id="upload-csv",
                children=dbc.Button(
                    "Upload CSV", id="upload-csv-btn", color="outline-primary", size="sm"
                ),
                accept=".csv",
                style={"display": "inline-block", "marginRight": 4},
            ),
            dbc.Button(
                "Load Sample Portfolio",
                id="load-sample-btn",
                color="outline-info",
                size="sm",
                style={"marginLeft": 4},
            ),
            html.Div(id="import-status", style={"marginTop": 4}),
            html.Hr(),
            html.H5("Your Portfolio"),
            dbc.InputGroup(
                [
                    dbc.Input(
                        id="ticker-input",
                        placeholder="Enter ticker(s) — comma-separated for multiple",
                        style={"textTransform": "uppercase"},
                    ),
                    dbc.Button("Add", id="add-ticker-btn", color="primary"),
                ]
            ),
            html.Div(feedback_rows, style={"marginTop": 4}),
            html.Div(portfolio_chips, style={"marginTop": 8}),
            dbc.Button(
                "Clear All",
                id="clear-portfolio-btn",
                size="sm",
                color="link",
                style={"marginTop": 4},
            ),
        ]
    )


@app.callback(
    Output("url", "pathname"),
    Input("btn-page-1", "n_clicks"),
    Input("btn-page-2", "n_clicks"),
    Input("btn-page-3", "n_clicks"),
    prevent_initial_call=True,
)
def navigate(n1, n2, n3):
    ctx = callback_context
    if not ctx.triggered:
        return "/"
    bid = ctx.triggered[0]["prop_id"]
    if "page-1" in bid:
        return "/"
    elif "page-2" in bid:
        return "/xray_map"
    elif "page-3" in bid:
        return "/recommend"
    return "/"


# ── CSV Import Callbacks ───────────────────────────────────────────────────────


def _parse_csv_contents(contents: str) -> dict | None:
    """Parse base64-encoded CSV content from dcc.Upload."""
    import base64

    if not contents or not contents.startswith("data:"):
        return None
    _, data = contents.split(",", 1)
    try:
        decoded = base64.b64decode(data).decode("utf-8")
    except Exception:
        return None
    try:
        from argus.core.ibkr_parser import parse_ibkr_csv

        return parse_ibkr_csv(decoded)
    except Exception:
        return None


def _load_sample_csv() -> dict | None:
    """Load the sample IBKR CSV from data directory."""
    sample_path = DATA_DIR / "sample_ibkr_portfolio.csv"
    if not sample_path.exists():
        return None
    try:
        from argus.core.ibkr_parser import parse_ibkr_csv

        return parse_ibkr_csv(sample_path.read_text())
    except Exception:
        return None


@app.callback(
    Output("store-import", "data"),
    Output("store-portfolio", "data", allow_duplicate=True),
    Output("import-status", "children"),
    Input("upload-csv", "contents"),
    Input("load-sample-btn", "n_clicks"),
    State("store-portfolio", "data"),
    prevent_initial_call=True,
)
def handle_csv_import(contents, sample_clicks, current_portfolio):
    ctx = callback_context
    if not ctx.triggered:
        return {"positions": [], "imported": False, "log": ""}, current_portfolio or [], ""

    trigger = ctx.triggered[0]["prop_id"]

    if "load-sample-btn" in trigger:
        result = _load_sample_csv()
    elif "upload-csv" in trigger and contents:
        result = _parse_csv_contents(contents)
    else:
        return {"positions": [], "imported": False, "log": ""}, current_portfolio or [], ""

    if result is None:
        return (
            {"positions": [], "imported": False, "log": "Failed to parse CSV"},
            current_portfolio or [],
            dbc.Alert("Failed to parse CSV file", color="danger", dismissable=True),
        )

    positions = result.get("positions", [])
    base_currency = result.get("base_currency", "USD")

    # Filter to ETFs in our universe
    in_universe = []
    out_of_universe = []
    for pos in positions:
        sym = pos.get("symbol", "").strip()
        if sym in ALL_TICKERS:
            in_universe.append(
                {
                    "ticker": sym,
                    "quantity": pos.get("quantity", 0),
                    "market_value": pos.get("market_value", 0),
                }
            )
        else:
            out_of_universe.append(sym)

    if not in_universe:
        log_msg = dbc.Alert(
            f"No ETFs found in portfolio that match our universe ({len(out_of_universe)} others skipped)",
            color="warning",
            dismissable=True,
            style={"fontSize": "12px", "padding": "4px 8px"},
        )
        return (
            {"positions": [], "imported": False, "log": str(out_of_universe)},
            current_portfolio or [],
            log_msg,
        )

    # Build new portfolio as list of {ticker, quantity, market_value}
    new_portfolio = in_universe

    universe_value = sum(p["market_value"] for p in in_universe)
    log_parts = [
        f"Imported {len(in_universe)} positions, total value {base_currency} {universe_value:,.0f}.",
    ]
    if out_of_universe:
        log_parts.append(f"{len(out_of_universe)} out-of-universe: {', '.join(out_of_universe)}.")

    log_msg = dbc.Alert(
        " ".join(log_parts),
        color="success",
        dismissable=True,
        style={"fontSize": "12px", "padding": "4px 8px"},
    )
    return (
        {"positions": in_universe, "imported": True, "log": "; ".join(log_parts)},
        new_portfolio,
        log_msg,
    )


@app.callback(
    Output("import-status", "children", allow_duplicate=True),
    Input("store-import", "data"),
    prevent_initial_call=True,
)
def show_import_status(import_data):
    if not import_data or not import_data.get("imported"):
        return ""
    return dbc.Alert(
        import_data.get("log", ""),
        color="success",
        dismissable=True,
        style={"fontSize": "12px", "padding": "4px 8px"},
    )


# ── Entry Point ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    port = 8050
    host = "0.0.0.0"
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        host = sys.argv[2]
    print(f"Starting Argus Dashboard on http://{host}:{port}")
    app.run(debug=False, use_reloader=False, port=port, host=host)
