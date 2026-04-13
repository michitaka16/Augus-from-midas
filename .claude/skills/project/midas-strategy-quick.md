# Midas Strategy — Quick Reference

## Regime Detection Ensemble

| Signal | Weight | Source | Stress Direction |
|---|---|---|---|
| HY OAS | 0.25 | FRED (1-day lag) / IBKR HYG-IEF proxy | Higher = more stress |
| VIX3M backwardation | 0.20 | VIX / VIX3M ratio | > 1.0 = backwardation = stress |
| Cross-sector PC1 | 0.20 | PCA on sector ETF returns | Higher variance = contagion |
| VIX level | 0.10 | FRED VIXCLS | Higher = stress |
| 200d SMA persistence | 0.10 | SPY vs 200d SMA | Negative days = stress |
| 21d realized vol | 0.10 | Annualized rolling std | Higher = stress |
| 3m10y yield curve | 0.05 | DGS10 - DGS3MO | Inverted = stress |

**Thresholds**: normal < 0.35, cautious 0.35-0.65, turbulent > 0.65
**Overrides**: drawdown -8% → cautious, -12% → turbulent; SPY/TLT corr > 0.3 → cautious

## 10 Asset Sleeves

| Sleeve | Primary Ticker | Liquidity |
|---|---|---|
| equity_sector | SPY | high |
| precious_metals | GLD | high |
| govt_bonds_short | SHY | high |
| govt_bonds_intermediate | IEF | high |
| govt_bonds_long | TLT | high |
| ig_corp_bonds | LQD | high |
| reits | VNQ | high |
| commodities | DJP | medium |
| dividend_etfs | VYM | high |
| em_equity | VWO | high |

## AAA Pipeline
momentum(6m) → top-K(regime) → min-variance(63d cov) → vol-target → turnover-penalty(10%/wk) → constraints(10d min-hold)

## Cost Model Components
IBKR commission ($0.0035/share, min $0.35) + SEC §31 (sells only) + FINRA TAF ($0.000119/share, cap $5.95) + half-spread slippage + Almgren-Chriss √(V/ADV) impact + gap risk
