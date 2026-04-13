"""
Yahoo Finance reconciliation adapter.

Used ONLY for cross-checking EODHD bars — never as a primary data source.

Legal caveat:
  yfinance has no SLA; commercial use is gray-area. Use ONLY for cross-check,
  never as primary. Consider Polygon/Tiingo before commercial launch.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class YahooClient:
    """Reconciliation-only wrapper around yfinance.

    yfinance is imported lazily — it is not a required dependency. If it is
    not installed, methods raise ``ImportError`` with an actionable message.
    """

    @staticmethod
    def _import_yfinance() -> Any:
        """Lazily import yfinance and return the module."""
        try:
            import yfinance  # noqa: WPS433 — intentionally lazy
        except ImportError:
            raise ImportError(
                "yfinance is required for Yahoo Finance reconciliation. "
                "Install it with: pip install yfinance"
            )
        return yfinance

    async def fetch_bars(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch EOD bars from Yahoo Finance for *ticker*.

        Runs the blocking yfinance download in an executor to avoid blocking
        the event loop.

        Returns a list of dicts with keys: date, open, high, low, close,
        adj_close, volume.
        """
        ctx = {"ticker": ticker, "start": str(start), "end": str(end), "source": "yahoo"}
        logger.info("yahoo.fetch_bars.start", **ctx)

        yf = self._import_yfinance()

        def _download() -> list[dict[str, Any]]:
            data = yf.download(
                ticker,
                start=str(start),
                end=str(end),
                progress=False,
                auto_adjust=False,
            )
            if data is None or data.empty:
                return []

            rows: list[dict[str, Any]] = []
            for idx, row in data.iterrows():
                rows.append(
                    {
                        "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                        "open": float(row.get("Open", 0.0)),
                        "high": float(row.get("High", 0.0)),
                        "low": float(row.get("Low", 0.0)),
                        "close": float(row.get("Close", 0.0)),
                        "adj_close": float(row.get("Adj Close", 0.0)),
                        "volume": int(row.get("Volume", 0)),
                    }
                )
            return rows

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _download)
        logger.info("yahoo.fetch_bars.ok", bars=len(result), **ctx)
        return result

    @staticmethod
    def reconcile(
        eodhd_bars: list[dict[str, Any]],
        yahoo_bars: list[dict[str, Any]],
        threshold: float = 0.005,
    ) -> list[dict[str, Any]]:
        """Compare EODHD bars against Yahoo bars and return disagreements.

        A disagreement is any trading day where
        ``|eodhd_close - yahoo_close| / eodhd_close > threshold`` (default
        0.5%).

        Both inputs must contain dicts with at least ``"date"`` and
        ``"close"`` keys. Returns a list of dicts describing each
        disagreement.
        """
        logger.info(
            "yahoo.reconcile.start",
            eodhd_bars=len(eodhd_bars),
            yahoo_bars=len(yahoo_bars),
            threshold=threshold,
        )

        yahoo_by_date: dict[str, dict[str, Any]] = {
            bar["date"]: bar for bar in yahoo_bars
        }

        disagreements: list[dict[str, Any]] = []

        for eodhd_bar in eodhd_bars:
            bar_date = eodhd_bar["date"]
            yahoo_bar = yahoo_by_date.get(bar_date)
            if yahoo_bar is None:
                continue

            eodhd_close = float(eodhd_bar["close"])
            yahoo_close = float(yahoo_bar["close"])

            if eodhd_close == 0.0:
                continue

            deviation = abs(eodhd_close - yahoo_close) / abs(eodhd_close)
            if deviation > threshold:
                disagreements.append(
                    {
                        "date": bar_date,
                        "eodhd_close": eodhd_close,
                        "yahoo_close": yahoo_close,
                        "deviation": round(deviation, 6),
                    }
                )

        logger.info(
            "yahoo.reconcile.ok",
            compared=len(eodhd_bars),
            disagreements=len(disagreements),
            threshold=threshold,
        )
        return disagreements
