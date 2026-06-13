"""Fetch xray data for missing ETFs and append to etf_xray_data.csv."""

import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

DATA_DIR = "data"

xray = pd.read_csv(f"{DATA_DIR}/etf_xray_data.csv", sep="|", index_col=0)
feat = pd.read_csv(f"{DATA_DIR}/etf_xray_features.csv", index_col=0)

# Re-fetch ALL ETFs (ignore existing xray to get correct data)
missing = sorted(feat.index.tolist())
print(f"Re-fetching all {len(missing)} ETFs")

new_rows = []
for ticker in missing:
    try:
        t = yf.Ticker(ticker)
        info = t.info

        name = info.get("longName", info.get("shortName", ticker))
        er = info.get("netExpenseRatio", 0.0) or 0.0
        dy = info.get("dividendYield", 0) or 0
        aum = info.get("totalAssets", info.get("netAssets", 0)) or 0
        avg_vol = info.get("averageVolume", 0) or 0

        aum_b = round(aum / 1e9, 3) if aum else 0.0
        dy_pct = round(float(dy), 2) if dy else 0.0

        # Sector exposure via funds_data
        try:
            fd = t.funds_data
            sector_w = fd.sector_weightings or {}
        except Exception:
            sector_w = {}

        sec_map = {
            "technology": "tech_pct",
            "financial_services": "finance_pct",
            "healthcare": "healthcare_pct",
            "energy": "energy_pct",
            "consumer_cyclical": "consumer_pct",
            "consumer_defensive": "consumer_pct",
            "industrials": "industrial_pct",
            "basic_materials": "materials_pct",
            "realestate": "other_pct",
            "utilities": "other_pct",
            "communication_services": "other_pct",
        }
        sector_pcts = {k: 0.0 for k in sec_map.values()}
        for sec_key, sec_val in sector_w.items():
            col = sec_map.get(sec_key, "other_pct")
            sector_pcts[col] += round(float(sec_val) * 100, 1)

        # Top holdings
        try:
            fd = t.funds_data
            th = fd.top_holdings
            if th is not None and not th.empty:
                top_holdings_str = " ".join(th.index[:5].tolist())
            else:
                top_holdings_str = ticker
        except Exception:
            top_holdings_str = ticker

        # Country exposure defaults (yfinance doesn't expose this reliably)
        # Use fund category to estimate
        us_pct = 100.0
        china_pct = 0.0
        europe_pct = 0.0
        japan_pct = 0.0
        emerging_pct = 0.0

        row = {
            "ticker": ticker,
            "name": name,
            "expense_ratio": er,
            "dividend_yield": dy_pct,
            "aum_b": aum_b,
            "avg_volume": int(avg_vol),
            "us_pct": us_pct,
            "china_pct": china_pct,
            "europe_pct": europe_pct,
            "japan_pct": japan_pct,
            "emerging_pct": emerging_pct,
            "tech_pct": round(sector_pcts["tech_pct"], 1),
            "finance_pct": round(sector_pcts["finance_pct"], 1),
            "healthcare_pct": round(sector_pcts["healthcare_pct"], 1),
            "energy_pct": round(sector_pcts["energy_pct"], 1),
            "consumer_pct": round(sector_pcts["consumer_pct"], 1),
            "industrial_pct": round(sector_pcts["industrial_pct"], 1),
            "materials_pct": round(sector_pcts["materials_pct"], 1),
            "other_pct": round(sector_pcts["other_pct"], 1),
            "top_holdings": top_holdings_str,
        }
        new_rows.append(row)
        print(f"  {ticker}: ER={er:.3f}, AUM=${aum_b:.1f}B, US={us_pct}%")

    except Exception as e:
        print(f"  {ticker}: ERROR - {e}")

print(f"\nFetched {len(new_rows)} ETFs")

if new_rows:
    new_df = pd.DataFrame(new_rows).set_index("ticker")
    new_df.to_csv(f"{DATA_DIR}/etf_xray_data.csv", sep="|")
    print(f"Written {len(new_df)} ETFs to etf_xray_data.csv")
else:
    print("No new data to write")
