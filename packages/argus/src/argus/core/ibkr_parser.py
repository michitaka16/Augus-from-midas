"""
Parser for Interactive Brokers Activity Statement CSV.
Handles the multi-section IBKR CSV format.

IBKR Activity Statements have this structure:
- Multiple sections, each with "Header" and "Data" rows
- Section name is the first column
- "Header" row defines columns for subsequent "Data" rows

We extract:
- Account info (name, currency)
- ETF positions from "Mark-to-Market Performance Summary"
  or "Open Positions" section (whichever exists)
"""

import csv
from io import StringIO


def parse_ibkr_csv(csv_content: str) -> dict:
    """
    Returns:
    {
      "account_name": str,
      "base_currency": str,
      "positions": [
        {"symbol": "VTI", "quantity": 100, "market_value": 25430.50,
         "cost_basis": 22000.00, "asset_category": "Stocks"},
        ...
      ],
      "total_value": float,
      "raw_section_count": int
    }
    """
    sections = {}  # section_name -> {"header": [...], "rows": [[...]]}
    current_section = None
    current_headers = None

    reader = csv.reader(StringIO(csv_content))
    for row in reader:
        if len(row) < 2:
            continue
        section = row[0]
        row_type = row[1]

        if row_type == "Header":
            current_section = section
            current_headers = row[2:]
            if section not in sections:
                sections[section] = {"header": current_headers, "rows": []}
            else:
                sections[section]["header"] = current_headers
        elif row_type == "Data" and current_section == section:
            sections[section]["rows"].append(row[2:])

    # Extract account info
    account_name = "Unknown"
    base_currency = "USD"
    if "Account Information" in sections:
        for row in sections["Account Information"]["rows"]:
            if len(row) >= 2:
                if row[0] == "Name":
                    account_name = row[1]
                elif row[0] == "Base Currency":
                    base_currency = row[1]

    # Extract positions
    positions = []
    position_sections = ["Open Positions", "Mark-to-Market Performance Summary"]
    for sec_name in position_sections:
        if sec_name not in sections:
            continue
        headers = sections[sec_name]["header"]
        if "Symbol" not in headers:
            continue

        sym_idx = headers.index("Symbol")
        cat_idx = headers.index("Asset Category") if "Asset Category" in headers else -1
        qty_idx = (
            headers.index("Quantity")
            if "Quantity" in headers
            else (headers.index("Current Quantity") if "Current Quantity" in headers else -1)
        )
        price_idx = headers.index("Current Price") if "Current Price" in headers else -1

        for row in sections[sec_name]["rows"]:
            if sym_idx >= len(row):
                continue
            symbol = row[sym_idx].strip()
            if not symbol or symbol == "Total":
                continue
            if cat_idx >= 0 and cat_idx < len(row):
                category = row[cat_idx]
                if category not in ("Stocks", "ETFs"):
                    continue
            else:
                category = "Unknown"

            try:
                qty = (
                    float(row[qty_idx])
                    if qty_idx >= 0 and qty_idx < len(row) and row[qty_idx]
                    else 0
                )
                price = (
                    float(row[price_idx])
                    if price_idx >= 0 and price_idx < len(row) and row[price_idx]
                    else 0
                )
                mkt_val = qty * price
            except ValueError:
                continue

            if qty > 0:
                positions.append(
                    {
                        "symbol": symbol,
                        "quantity": qty,
                        "current_price": price,
                        "market_value": mkt_val,
                        "asset_category": category,
                    }
                )
        break  # Use first matching section

    total_value = sum(p["market_value"] for p in positions)

    return {
        "account_name": account_name,
        "base_currency": base_currency,
        "positions": positions,
        "total_value": total_value,
        "raw_section_count": len(sections),
    }


if __name__ == "__main__":
    import sys

    with open(sys.argv[1]) as f:
        result = parse_ibkr_csv(f.read())
    import json

    print(json.dumps(result, indent=2))
