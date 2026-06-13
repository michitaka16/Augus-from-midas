"""
ibkr_parser.py — Parse Interactive Brokers Activity Statement CSV exports.

The IBKR Activity Statement CSV format has multiple sections separated by
"Section,Header,..." lines. The relevant section for portfolio positions is
"Mark-to-Market Performance Summary" which contains:
  Symbol | Asset Category | Quantity | Currency | Current Price |
  Market Value | Cost Basis | Unrealized P/L | Percent of Portfolio

Returns:
    {
        "positions": [{"symbol": str, "quantity": float, "market_value": float}, ...],
        "total_value": float,
        "base_currency": str,
        "account_name": str,
    }
"""

from __future__ import annotations

import csv


def parse_ibkr_csv(csv_content: str) -> dict | None:
    """
    Parse an IBKR Activity Statement CSV and extract ETF positions.

    Handles the Mark-to-Market Performance Summary section which lists
    all positions with quantity and market value.
    """
    try:
        lines = csv_content.strip().splitlines()
    except Exception:
        return None

    if not lines:
        return None

    # State machine to find the Mark-to-Market section
    in_m2m_section = False
    header_row: list[str] = []
    positions: list[dict] = []
    total_value = 0.0
    base_currency = "USD"
    account_name = "Unknown"

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            row = list(next(csv.reader([line])))
        except Exception:
            continue

        if len(row) < 2:
            continue

        section = row[0]
        sub_type = row[1] if len(row) > 1 else ""

        # Detect M2M section entry
        if sub_type == "Header" and "Mark-to-Market Performance Summary" in section:
            # Column headers are embedded in same row after the section name
            # e.g. "Mark-to-Market Performance Summary,Header,Symbol,Asset Category,..."
            in_m2m_section = True
            header_row = row[2:] if len(row) > 2 else []
            continue

        if sub_type == "Header" and section == "Statement" and len(row) > 2:
            if "Mark-to-Market Performance Summary" in row[2]:
                in_m2m_section = True
                continue
            else:
                in_m2m_section = False

        if in_m2m_section:
            if sub_type == "Header":
                # Column header row (e.g. Symbol,Asset Category,Quantity,...)
                header_row = row[2:] if len(row) > 2 else []
                continue
            elif sub_type == "Data":
                if not header_row:
                    continue
                # Data row
                values = row[2:] if len(row) > 2 else []
                if len(values) < len(header_row):
                    values = values + [""] * (len(header_row) - len(values))

                row_dict = dict(zip(header_row, values, strict=True))

                symbol = row_dict.get("Symbol", "").strip()
                asset_category = row_dict.get("Asset Category", "").strip()
                quantity_str = row_dict.get("Quantity", "").strip()
                market_value_str = row_dict.get("Market Value", "").strip()
                currency_str = row_dict.get("Currency", "").strip()

                # Skip Total row and non-ETF rows
                if not symbol or symbol.lower() == "total":
                    continue
                if asset_category.lower() != "etfs":
                    continue

                try:
                    quantity = float(quantity_str) if quantity_str else 0.0
                except ValueError:
                    quantity = 0.0

                try:
                    market_value = float(market_value_str) if market_value_str else 0.0
                except ValueError:
                    market_value = 0.0

                if market_value > 0:
                    positions.append(
                        {
                            "ticker": symbol.upper(),
                            "quantity": quantity,
                            "market_value": market_value,
                        }
                    )
                    total_value += market_value

                if currency_str:
                    base_currency = currency_str
                continue

        # Extract account metadata from Statement,Data rows
        if section == "Statement" and sub_type == "Data" and len(row) >= 4:
            key = row[2].strip()
            val = row[3].strip()
            if key == "Account":
                account_name = val
            elif key == "Base Currency":
                base_currency = val

    if not positions:
        return None

    return {
        "positions": positions,
        "total_value": total_value,
        "base_currency": base_currency,
        "account_name": account_name,
    }
