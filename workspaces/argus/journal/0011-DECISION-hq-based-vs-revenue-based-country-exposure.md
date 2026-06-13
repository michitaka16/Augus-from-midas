---
type: DECISION
date: 2026-04-19
created_at: 2026-04-19T00:00:00
author: co-authored
session_id: current
project: argus
topic: Country exposure data limitation — headquarters-based vs revenue-based classification
phase: implement
tags: [data-quality, country-exposure, feature-limitations, hq-based, revenue-based]
---

## Decision: Country Exposure Data Limitation — HQ-Based vs Revenue-Based

### The Data Problem

ETF country exposure is ambiguous because ETFs hold underlying securities (stocks, bonds) that themselves have multi-country revenue streams and operations. The question: what does "country exposure" mean for an ETF?

### Option A: Headquarter-Based Classification

Classify each ETF by the headquarters location of its underlying holdings' issuers.
Example: VEA (which holds European and Japanese stocks) is classified as "non-US" because its holdings are headquartered in Europe/Japan.

**Pros**: Available from ETF provider factsheets and standard databases. Matches how most data providers report country exposure. Binary classification is simple to implement and explain.

**Cons**: Misrepresents economic exposure. A US-tech company with 60% revenue from Asia (Apple, Qualcomm) would be classified as US equity under HQ-based classification, even though economic exposure is partly Asian. A European bank with heavy US operations would be classified as non-US despite earning 70% of revenue from the US.

### Option B: Revenue-Based Classification

Classify each holding by the geographic source of its revenues (as disclosed in SEC filings for US companies or equivalent disclosures for international companies).

**Pros**: Economically accurate. A US-headquartered company earning 60% of revenue from Asia is correctly classified as 60% Asia exposure.

**Cons**: Requires per-holding revenue breakdown data not available in standard ETF factsheets. Requires proprietary datasets (FactSet, MSCI, Bloomberg geography data). Cost and licensing implications. Revenue attribution changes over time and requires periodic updates.

### Selected Approach: HQ-Based with Acknowledged Limitation

The current implementation uses headquarter-based country exposure from `etf_universe.csv`.

**Specific limitation**: VWO (emerging markets) and EEM (emerging markets) receive the same country_exposure score as VEA (developed international) under the binary US/non-US classification, despite fundamentally different geographic compositions. EEM has high EM Asia exposure; VEA does not. This is not captured.

**Flagged ETF compromise**: For the Geopolitical Screen specifically, VWO and EEM are placed in `flagged_etfs` to short-circuit the similarity logic — they are excluded from the cluster similarity system and flagged as hard violations regardless of their feature-vector similarity to compliant ETFs. This is a compliance override, not a data fix.

**Acknowledged trade-off**: For clustering quality (K-means on 23 ETFs), HQ-based is sufficient to separate US equity ETFs from international. For compliance rules that enforce country allocation limits at precision (e.g., "max 10% China exposure"), HQ-based is insufficient and revenue-based classification is required.

**Commercial version requirement**: Revenue-based or geographic-origin classification is a required data enhancement for a production-grade compliance module.

## For Discussion

1. Are there free or low-cost data sources for revenue-based country exposure at the individual stock level? MSCI and S&P provide this for institutional clients, but are there open-source alternatives (e.g., derived from 10-K disclosures)?

2. For the demo, should we manually override the country classification for the most economically significant misclassifications (e.g., manually label EEM and VWO as having EM Asia exposure, VEA as developed international only) to improve clustering quality without requiring a data purchase?

3. The `flagged_etfs` approach is a compliance shortcut. Is it better to keep it (it works correctly for the demo) or replace it with a proper revenue-based classification for all ETFs, even if that requires a data enhancement?
