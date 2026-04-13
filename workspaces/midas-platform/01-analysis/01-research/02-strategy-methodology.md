# Strategy Methodology — Midas Platform

Status: research doc, phase 01. Scope: asset sleeve definition, regime detection, rotation/allocation, multi-horizon design, transaction cost model, backtest methodology. Audience: next phase (planning / todos). Numbers cited from published literature are memorized; live web search was denied in this session, so primary sources are named for later verification rather than linked.

Note on independence: this document is strategy research for the Midas portfolio management application. It is not part of the Kailash SDK and does not reference or depend on any commercial product.

---

## 1. Asset Sleeves and Liquid IBKR-Accessible ETFs

Brief requires: equity sector ETFs, precious metals, government bonds (all durations), IG corporate bonds, REITs, commodities, dividend funds, emerging markets. Selection criteria: (a) daily dollar volume > $50M to keep slippage below 3 bps at realistic trade sizes, (b) expense ratio < 50 bps where possible, (c) >= 10 years of history so the backtest from 2000 can splice in the underlying index before inception, (d) IBKR accessible with no PTP / K-1 gotchas where avoidable.

**1.1 Equity sector ETFs (SPDR Select Sector, 11 GICS sectors).** XLK (Tech), XLF (Financials), XLV (Health Care), XLY (Consumer Discretionary), XLP (Consumer Staples), XLE (Energy), XLI (Industrials), XLB (Materials), XLU (Utilities), XLRE (Real Estate, 2015+), XLC (Communication, 2018+). Expense ratio 0.09%. History to 1998 for the original nine. Behavior: XLU and XLP are defensive (beta ~0.5, outperform in drawdowns); XLK, XLY, XLF are pro-cyclical (beta ~1.2); XLE is commodity-levered with fat tails. For the two newest sectors pre-inception, splice with their parent S&P index constituents. Alternative universe: iShares sector (IYW, IYF etc.) at 0.39% — more expensive, skip unless a specific tilt is needed.

**1.2 Precious metals.** GLD (SPDR Gold, ER 0.40%), IAU (iShares Gold, ER 0.25% — preferred for cost), SLV (Silver, ER 0.50%). Optional miner beta via GDX (ER 0.51%). Crisis behavior: gold is the canonical flight asset but correlation to equities is unstable; in 2008 gold initially sold off during the liquidity crunch before rallying. In 2022 gold was flat while both stocks and bonds fell double digits — its value as a diversifier is regime-dependent, not unconditional. Use IAU as primary gold sleeve.

**1.3 Government bonds by duration.**
- Short: SHY (1–3y Treasury, ER 0.15%) or BIL (1–3m T-bill, ER 0.14%) for true cash-equivalent.
- Intermediate: IEI (3–7y, 0.15%), IEF (7–10y, 0.15%).
- Long: TLT (20+y, 0.15%), EDV (STRIPS, 0.06%, higher duration ~24y for turbulent-regime convexity).
- TIPS overlay: TIP (0.19%) or SCHP (0.03%) for real-rate exposure — useful in 2021–2022 style inflation shocks where nominal bonds lose the stock-bond hedge.

Historical behavior: long Treasuries were the dominant crisis hedge 2000–2019 (correlation to SPX around -0.3, spiking to -0.6 in drawdowns). In 2022 that hedge inverted: SPX and TLT both drew down >20% as inflation broke the negative-correlation regime. The strategy MUST NOT assume bonds always hedge equities — regime detection has to flag when the stock/bond correlation is positive and rotate into cash-like SHY/BIL plus gold.

**1.4 IG corporate bonds.** LQD (iShares IG Corporate, ER 0.14%), VCIT (Vanguard 5–10y IG, ER 0.04% — preferred). In crises LQD widens with HY but less; in 2020 March LQD fell ~22% before Fed SMCCF intervention — treat IG as "equity-lite" in turbulent regimes, not as a ballast substitute.

**1.5 REITs.** VNQ (Vanguard, ER 0.13% — preferred), IYR (iShares, 0.39%). REITs behave like leveraged equity + rates duration. Correlation to SPX ~0.75, correlation to TLT ~0.3. In 2008 VNQ fell 70% peak to trough. Treat as satellite equity sleeve, not as diversifier.

**1.6 Commodities.** DBC (Invesco DB Commodity, ER 0.85%, issues K-1 — avoid), PDBC (no K-1 version, 0.59%), GSG (iShares S&P GSCI, 0.75%), COMB (GraniteShares, 0.25% — preferred for cost and no K-1). Behavior: commodities are an inflation hedge; 2022 was the only positive major-asset sleeve. Long-run real return is near zero — use tactically, not strategically.

**1.7 Dividend funds.** VYM (Vanguard High Dividend Yield, ER 0.06%), SCHD (Schwab US Dividend Equity, 0.06%), DVY (iShares Select Dividend, 0.38%). SCHD's quality screen (5y dividend growth, ROE, cash-flow-to-debt) has delivered the lowest drawdown of the three through 2015–2025. Use SCHD as primary dividend sleeve.

**1.8 Emerging markets.** VWO (Vanguard, ER 0.08%), IEMG (iShares Core, 0.09%), EEM (iShares MSCI EM, 0.70% — avoid on cost). Optionally split DM-EM via EEMS (small cap) or split China out via MCHI/KWEB if the allocator wants to express a regional view. Behavior: EM equity has higher beta to global risk-on than DM (around 1.2 vs SPX) and elevated drawdowns in USD strength episodes.

**Pre-inception splicing.** For sleeves where the ETF does not reach 2000-01-01, the backtest uses the underlying index total return (S&P 500 sector indices, Bloomberg US Treasury indices, FTSE NAREIT, S&P GSCI) minus a synthetic tracking-error of 10 bps annualized and the current expense ratio. This is disclosed in every backtest report so the user knows which periods are "real fund" and which are "index proxy."

---

## 2. Regime Detection — Literature Review and Ensemble Recommendation

The brief requires freezing auto-trading in "turbulent" regimes and running normal allocation otherwise. The assumption doc already commits to a multi-signal ensemble. The question this section answers: which signals, what thresholds, how to combine them.

**2.1 VIX level and term structure.** VIX is the 30-day implied volatility of SPX options. Level regimes from decades of data: <15 complacent, 15–20 normal, 20–30 elevated, >30 stressed, >40 crisis. VIX level alone is a weak timing signal because it is coincident with drawdowns rather than leading. The more useful signal is the **VIX / VIX3M ratio** (VIX3M = 93-day forward vol index). Backwardation (ratio > 1.0) is historically an excellent regime-flip signal: it happens on fewer than 10% of trading days and precedes most multi-week equity drawdowns in the 2008–2024 sample (Simon & Campasano 2014; CBOE research notes; various practitioner writeups). Complementary signal: **VVIX** (vol of VIX), where sustained VVIX > 100 with rising VIX is characteristic of regime breaks. Threshold recommendation: VIX3M backwardation for >= 3 consecutive sessions OR VIX > 30 triggers "turbulent."

**2.2 Realized volatility (RV).** GARCH(1,1) on daily SPX returns gives a smoothed conditional vol estimate; HAR-RV (Corsi 2009) is a simpler model that regresses daily RV on daily, weekly, and monthly lagged RV and has outperformed GARCH out-of-sample in several comparative studies. For this project, use **5-day and 21-day realized vol annualized**, with thresholds 5d RV > 25% OR 21d RV > 20% flagging "cautious." Realized vol is lagging but confirms forward-looking VIX signals.

**2.3 HMM / Markov switching.** Hamilton (1989) introduced the two-state Markov switching model; Ang & Bekaert (2002) and Guidolin & Timmermann (2007) applied it to asset allocation. Practical experience: HMM fitted on returns alone tends to overfit and switches regimes late. Fitted on a feature vector (returns + VIX + credit spreads + yield curve) via Gaussian HMM, it produces more stable 2- or 3-state labels but is hard to interpret and introduces a hyperparameter (number of states) that the backtest has to grid-search. Recommendation: implement HMM as a **diagnostic overlay** (shown in UI as a learned regime label) but do NOT make it the trading gate in v1 — it is opaque and failure modes are hard to explain to the user in plain language.

**2.4 Trend filters.** Faber (2007, "A Quantitative Approach to Tactical Asset Allocation") showed that a simple 10-month SMA filter on each sleeve (own the sleeve when price > 10m SMA, go to cash otherwise) reduces drawdowns substantially across a 1973–2005 sample and has held up reasonably out of sample through 2024. Equivalent daily formulation is the 200-day SMA. Trend filters have a well-known weakness: they whipsaw in choppy markets (2015–16, 2018 Q4). Recommendation: use **SPX vs 200d SMA as a confirmatory signal** — combined with a minimum "persistence" requirement (SPX below SMA for >= 5 consecutive days) to suppress whipsaw.

**2.5 Credit spreads (HY OAS).** ICE BofA US High Yield OAS is one of the most reliable macro stress indicators. Long-run median around 450 bps; >600 bps historically flags recession/stress, >800 bps flags crisis (2008, 2020). The signal is slower than VIX (OAS widens over weeks) but has far fewer false positives. Threshold: HY OAS > 550 bps OR HY OAS month-over-month change > +100 bps flags "cautious"; > 700 bps flags "turbulent."

**2.6 Yield curve.** 2s10s and 3m10y inversions are well-documented leading recession indicators (Estrella & Mishkin 1998; NY Fed model). The 3m10y inversion has a shorter false-positive history than 2s10s. For short-term tactical allocation the yield curve is too slow — an inversion can precede a market peak by 12–24 months. Use it as a **risk-budget dampener** (reduce gross exposure by 10–20% while inverted) not as a regime gate.

**2.7 Cross-asset correlation breakdown.** In normal regimes, SPX/TLT correlation is negative and intra-sector dispersion is meaningful. In crises, "everything goes to one" — the first PC explains >80% of daily variance across sectors. Signal: rolling 21-day first PC explained variance on a basket of 11 sectors + TLT + LQD + GLD; when it crosses 75%, the diversification assumptions of the allocator break down and the system should de-risk. This is the signal most directly aligned with the brief's "no free lunch, agile rotation" thesis — it measures exactly when rotation stops working.

**2.8 Drawdown kill switch.** Independent of any model: if the portfolio drawdown from its trailing 252-day peak exceeds a fixed threshold, halt auto-trading regardless of what the regime ensemble says. Recommendation: **-8% soft halt (notify user, require approval), -12% hard halt (flatten equity sleeves to cash)**. This is the user's stated risk preference operationalized: "go big but not stupid" means accept tail exposure up to a point, then stop.

**2.9 Recommended ensemble.** Each signal emits {-1, 0, +1} for {cautious, normal, turbulent}. Weighted sum with the following weights (rationale: credit and correlation are the most reliable at regime boundaries; VIX term structure is fast; trend is confirmatory):

| Signal | Weight | Normal | Cautious | Turbulent |
|---|---|---|---|---|
| HY OAS level & delta | 0.25 | <500 and dMoM<50 | 500–700 or dMoM 50–100 | >700 or dMoM >100 |
| VIX3M backwardation (3d persistent) | 0.20 | contango | ratio 0.98–1.02 | backwardation |
| Cross-sector PC1 variance (21d) | 0.20 | <60% | 60–75% | >75% |
| VIX level | 0.10 | <20 | 20–30 | >30 |
| SPX vs 200d SMA (5d persistent) | 0.10 | above | crossing | below |
| 21d realized vol | 0.10 | <15% | 15–25% | >25% |
| Yield curve (3m10y) | 0.05 | positive | flat | inverted |
| Drawdown from 252d peak | override | >-5% | -5% to -8% | <-8% |

Regime label: **Normal** if weighted score <= -0.3 (negative means calm here); **Cautious** if -0.3 to +0.3; **Turbulent** if >= +0.3. The drawdown gate is a hard override — any drawdown past -8% forces at minimum Cautious, past -12% forces Turbulent + flatten.

Hysteresis: require 2 consecutive daily closes in a new regime before switching, to reduce oscillation. All thresholds are hyperparameters exposed in config, NOT hardcoded, so walk-forward tuning can perturb them.

---

## 3. Rotation and Allocation — Primary + Fallback

The allocator must respect: weekly-max rebalance, cost awareness, multi-horizon robustness, "go big" tilt in normal regimes.

**3.1 Candidate methods.**
- *Equal risk contribution (ERC, Maillard-Roncalli-Teïletche 2010)*: each asset contributes equally to portfolio variance. Robust, no return estimate needed, but agnostic to momentum — it will happily overweight a bleeding sleeve because its vol is low.
- *Hierarchical risk parity (HRP, López de Prado 2016)*: uses a correlation-distance dendrogram to cluster assets, then recursive bisection for weights. More stable than ERC when the covariance matrix is ill-conditioned (which it is, for 20+ sleeves on daily data). Demonstrated out-of-sample turnover advantage over minimum variance.
- *Dual momentum (Antonacci 2014)*: absolute momentum (12m return > T-bill) as a gate, relative momentum to pick winners. Simple, transparent, works across decades, but concentrated — picks a small number of sleeves, so intra-regime rotation is discrete and high-turnover at boundaries.
- *Adaptive asset allocation (Butler-Philbrick-Gordillo 2012, "AAA")*: top-N by momentum, then minimum variance weights within the top-N. Explicitly combines trend with diversification.
- *Vol-targeted risk parity*: ERC scaled so ex-ante portfolio vol hits a target (e.g. 12% normal, 8% cautious, 0% turbulent).
- *Min variance and max diversification*: theoretically clean, empirically fragile due to covariance estimation error; not recommended as primary.
- *Black-Litterman with regime-conditional views*: elegant but adds a free parameter (view strength, "tau") that is hard to tune autonomously.

**3.2 Recommendation — primary: Adaptive Asset Allocation (AAA) with regime-conditional vol target.** Each week:
1. Rank all sleeves by blended momentum score (Section 4).
2. Select top-K (K=6 in normal, K=4 in cautious, K=0 in turbulent — when turbulent, park in SHY/BIL + IAU at fixed weights).
3. Within the selected set, compute minimum-variance weights on the 60-day covariance matrix.
4. Scale the resulting weight vector so ex-ante annualized portfolio volatility equals the regime vol target (normal 14%, cautious 8%, turbulent cash).
5. Apply a turnover penalty (Section 4) that keeps weights close to last week's weights unless the improvement in Sharpe is meaningful.

This satisfies the brief: "go big" via the vol target in normal regimes, agile rotation via momentum ranking, diversification within the winners via min-var, automatic de-risk via vol target shrinkage when the covariance regime shifts.

**3.3 Recommendation — fallback: HRP on the full sleeve set, vol-targeted.** If the momentum-ranked AAA is tripped (e.g. momentum scores are all within 1 standard error of each other, indicating no signal), fall back to HRP which doesn't need a return forecast. HRP on the full sleeve set with the same vol target is a graceful degradation rather than a switch to an entirely different philosophy.

---

## 4. Multi-Horizon Signal Blending Without Whipsaw

The brief explicitly requires multiple sub-horizons. Naive approaches (average three momentum windows) do reduce whipsaw but can also mask real regime changes. Recommendation: **hierarchical blending with turnover penalty**.

**4.1 Horizon definitions and signal construction.**
- *Short (1–3 month)*: 63-day return minus 5-day return. The 5-day subtraction removes very recent noise / gap risk that would whipsaw the allocator.
- *Medium (6–12 month)*: blended score 0.5 * 126d return + 0.5 * 252d return, following Asness-Moskowitz-Pedersen "Value and Momentum Everywhere" which found this window most persistent.
- *Long (2–5 year)*: 756d return z-score relative to the cross-section, used only to break ties and to dampen short-term signals that contradict long-term trend.

Each horizon produces a cross-sectional z-score per sleeve. Composite score = 0.25 * short + 0.50 * medium + 0.25 * long. The medium weight is highest because 6–12m momentum has the strongest out-of-sample edge in the published cross-section (Jegadeesh-Titman, Asness).

**4.2 Turnover penalty.** Objective function for the weekly optimization:

```
maximize   w^T * mu_composite  -  lambda_var * w^T * Sigma * w  -  lambda_turn * ||w - w_prev||_1
subject to sum(w) = 1, w >= 0, per-sleeve cap <= 25%, sector-family cap <= 50%
```

The L1 turnover penalty is critical: it has a closed-form effect that no trade is executed unless the improvement in expected utility exceeds twice the round-trip cost. Set `lambda_turn` so that, at the cost function from Section 5, a 1% weight change requires ~15 bps of expected improvement. This makes the turnover penalty *cost-aware* in units that are directly comparable to the commission + slippage estimate.

**4.3 Anti-whipsaw guardrails.**
- Minimum hold period: a sleeve that has just been sold cannot be rebought for 10 trading days unless the composite score moves >1 standard deviation.
- Weekly rebalance cap: weight changes capped at 10% per sleeve per week regardless of optimizer output.
- Regime hysteresis (Section 2.9): regime transitions require 2 consecutive days.

These three layers together produce a realized turnover target of roughly 150–250% per year, well below the ~400% of naive momentum, which is the single biggest driver of post-cost decay in published studies.

---

## 5. Transaction Cost Model

The brief is emphatic about realistic costs, including fees, commissions, slippage, impact, and gap risk. The cost function below is designed to plug directly into the backtester and the live order-placement preview.

**5.1 IBKR Pro commissions (US stocks & ETFs, fixed tier).** $0.005 per share, min $1.00 per order, max 1.0% of trade value. For the Pro tiered schedule (volume-dependent): tiers start at $0.0035/share (<300k shares/month) and drop to $0.0005/share at the largest tier. Assume the fixed $0.005/share tier for v1 sizing — it is the worst case for a retail account under $1M. For a $20k trade in a $50 ETF that is 400 shares * $0.005 = $2.00 commission = 1.0 bps. For a $5k trade in a $50 ETF that is 100 shares * $0.005 = $0.50, rounded to $1.00 minimum = 2.0 bps.

**5.2 Regulatory fees (US sells only).** SEC Section 31 fee: rate is reset periodically and was 27.8 usd per million of sale proceeds in fiscal 2024; budget 30 usd/million to be safe. FINRA TAF: $0.000166 per share, max $8.30 per trade. NSCC, OCC, and exchange fees are pass-through through IBKR and are generally < 0.1 bps for liquid ETFs. Regulatory fees apply on sells only.

**5.3 Half-spread slippage.** For the ETFs in the sleeve universe, typical bid-ask spreads in regular trading hours are 1 cent for tier-1 (SPY, TLT, GLD, IEF, XLK etc.) and 1–3 cents for tier-2 (VNQ, SCHD, VWO, etc.). Half-spread in bps = (0.5 * spread / mid-price) * 10000. For a $50 ETF with a 1c spread, half-spread = 1.0 bps. Implementation: store a per-ETF "typical half-spread in bps" table calibrated from historical L1 data (EODHD provides this) and vary it with VIX — in turbulent regimes spreads widen 2–3x.

**5.4 Market impact (Almgren-Chriss square-root law).** For order size Q as a fraction of average daily volume ADV, temporary impact is typically modeled as `eta * sigma * sqrt(Q / ADV)` where sigma is daily volatility and eta is a constant ~0.1 for US equities (Almgren-Thum-Hauptmann-Li 2005). For the Midas sleeve universe with realistic trade sizes (< 0.5% of ADV for liquid ETFs at <$1M account size), the square-root term is small: sqrt(0.005) * 0.01 * 0.1 = 0.7 bps. For the illiquid REIT and commodity ETFs at > $500k per trade, impact can reach 5–10 bps. Budget impact as `max(0.5 bps, 10 * sqrt(trade_value / ADV_usd))` as a conservative parametric approximation.

**5.5 Gap risk.** ETF opens gap relative to the prior close driven by overnight futures, FX, and pre-market news. For the sleeve universe the 95th percentile absolute gap is around 50 bps for equity sleeves and 30 bps for bond sleeves. This is not a "cost" in the commission sense but it IS a realized return the backtester must attribute correctly: all orders are assumed to execute at next-session open (or VWAP if the user chooses), and the slippage-to-arrival-price metric must be logged so the user can see whether the cost model matches reality.

**5.6 Total cost function to plug into the backtest.**

```
cost_per_trade(side, ticker, notional, adv_usd, spread_bps, regime_vol_multiplier):
  commission_bps = max(1.0 * 10000 / notional, 0.005 * shares * 10000 / notional)  # min $1 floor
  commission_bps = min(commission_bps, 100)                                         # 1% cap
  reg_bps        = 3.0 if side == 'SELL' else 0.0                                   # SEC + FINRA
  half_spread    = 0.5 * spread_bps * regime_vol_multiplier
  impact_bps     = max(0.5, 10 * sqrt(notional / adv_usd))
  slippage_bps   = half_spread + impact_bps
  return commission_bps + reg_bps + slippage_bps
```

Round-trip cost in a normal regime for a liquid ETF at $20k notional: ~1 (comm) + 1.5 (half-spread) + 0.5 (impact) + 3 (sell-side reg) = **~6 bps round trip**. For a tier-2 ETF in a turbulent regime (spread 3x): ~1 + 4.5 + 2 + 3 = **~10–15 bps round trip**. These numbers determine the turnover penalty in Section 4.2.

**5.7 Calibration loop.** Every live fill is logged with (arrival price, fill price, commission, regulatory fee). Weekly job computes realized cost vs modeled cost per ticker and regime. If realized exceeds modeled by > 2x for 4 weeks in a row, raise an alert and re-calibrate the spread and impact constants. This prevents silent backtest-vs-live divergence.

---

## 6. Backtest Methodology

**6.1 Walk-forward.** The canonical training/test split: train on an expanding window, test on the next period, roll forward, retrain. For the Midas allocator the expanding window starts at 2000-01-01 through 2004-12-31 (~5y), tests on 2005, expands and retests, etc. Hyperparameters (regime thresholds, lambda_turn, vol targets, top-K) are re-tuned at each walk-forward step using only information available at that time.

**6.2 Purged k-fold.** Standard k-fold CV leaks information when consecutive samples are correlated — which is exactly the case for daily asset returns because signals use 126–756 day lookbacks. López de Prado's "Advances in Financial Machine Learning" (2018) proposes **purged k-fold**: after splitting into folds, drop training observations whose label window overlaps the test fold, plus an "embargo" of a few days after the test fold to eliminate serial-correlation leakage. The embargo length should equal the longest feature lookback (756 days for the long-horizon signal). This is expensive — it discards a lot of training data — but without it, backtest Sharpe is systematically inflated.

**6.3 Combinatorial purged CV (CPCV).** Also López de Prado. Instead of one walk-forward path, generate many paths by leaving out multiple non-adjacent folds as the test set. Gives a distribution of out-of-sample performance instead of a single number, which is what the user actually needs to make a trust decision. Target: report backtest Sharpe as median and 5th/95th percentile across CPCV paths, not as a point estimate.

**6.4 Look-ahead elimination.**
- All features computed with strictly lagged data (use T-1 close for signals applied at T open).
- Fundamental / sector rotation data (e.g. GICS classification changes) must be point-in-time. Use the GICS change log.
- Regime signals (VIX, HY OAS) must use the **publication-day** value, not the as-of-date value: HY OAS is published with a 1-day lag.
- Rebalance prices use **next-day open** not same-day close. This alone reduces naive backtest Sharpe by ~0.2 for momentum strategies on daily data.

**6.5 Survivorship bias.** The current ETF sleeve list is not the 2000-era ETF sleeve list — SCHD (2011), XLRE (2015), XLC (2018) didn't exist. Options: (a) splice with underlying index, disclosed; (b) use only ETFs that existed at the test date, which shrinks the pre-2011 universe. The report must show both "as-available universe" and "modern universe with index proxy" results side by side so the user can see how much of the reported edge depends on post-2015 instruments.

**6.6 Stress windows.** In addition to rolling Sharpe and CPCV distribution, the report must include per-crisis summaries: 2000–02 dot-com, 2008 GFC, 2011 EU debt, 2015–16 China/oil, 2018 Q4 vol shock, 2020 COVID, 2022 rates shock, 2023 banking stress. For each window: max drawdown, days to recover, hit rate vs buy-and-hold 60/40, regime classifier accuracy (did it flag "turbulent" before the drawdown exceeded -8%?). These windows are what the user will actually look at — rolling Sharpe is academic, per-crisis behavior is what drives trust.

**6.7 Overfitting controls.** Bailey-Borwein-López de Prado "Probability of Backtest Overfitting" (PBO) metric computed from CPCV paths; reported alongside the headline Sharpe. Deflated Sharpe Ratio (López de Prado 2014) adjusts for number of trials and non-normal returns — report this instead of raw Sharpe whenever we have tuned hyperparameters on the same data.

---

## 7. Open Questions for the Next Phase

These are NOT gaps to be deferred (zero-tolerance rule); they are items to raise at the next human gate:

1. Does the user want the turbulent regime to flatten equities entirely, or reduce to 25% gross and hold? Brief says "don't trade without my permission" which is closer to flatten-and-halt.
2. Vol targets (14% normal / 8% cautious) define "go big." User should confirm these map to the risk appetite.
3. Pre-2011 backtest: does the user want (a) real-ETF-only (short history, no SCHD/XLRE/XLC) or (b) full-length with index splicing? Recommendation (a) is primary, (b) shown as supplementary.
4. The momentum z-score uses sleeve cross-section. Does it also need a benchmark-relative component (vs SPX) for the equity sleeves?

---

## 8. Summary Table

| Component | Choice | Rationale |
|---|---|---|
| Regime detector | Weighted ensemble: HY OAS (0.25), VIX3M backwardation (0.20), cross-sector PC1 (0.20), VIX (0.10), 200d SMA (0.10), RV (0.10), yield curve (0.05); drawdown hard override | Credit + correlation breakdown are the most reliable leading indicators; VIX term structure is fast; trend is confirmatory; single signals produce too many false positives |
| Primary allocator | Adaptive Asset Allocation (top-K momentum + min-var within, vol-targeted, turnover-penalized) | Satisfies "go big" via vol target, agile rotation via momentum, diversification via min-var, cost discipline via turnover penalty |
| Fallback allocator | Hierarchical Risk Parity on full sleeve set, vol-targeted | Degrades gracefully when momentum signal is flat; no return estimate required |
| Multi-horizon | 0.25 short (63d-5d) + 0.50 medium (0.5 * 126d + 0.5 * 252d) + 0.25 long (756d), with L1 turnover penalty, 10-day min-hold, weekly 10% weight cap | Matches published cross-sectional momentum edge; turnover penalty is cost-aware in bps |
| Cost model | IBKR Pro $0.005/sh min $1 + SEC 30/mil + FINRA TAF + half-spread (regime-scaled) + sqrt-of-ADV impact | Matches published Almgren-Chriss impact and IBKR fee schedule; calibrated weekly against realized fills |
| Backtest | Walk-forward + CPCV + 756d embargo + point-in-time regime data + index-spliced pre-inception + per-crisis stress windows + DSR / PBO reporting | Matches López de Prado FinML best practice; specifically addresses look-ahead, survivorship, and overfitting |
