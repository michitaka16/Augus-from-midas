"""
IBKR HY ETF spread proxy for intraday credit-spread estimation.

Computes the HYG-IEF spread as an intraday proxy for HY OAS, used when
FRED's ~1-day publication lag matters (e.g., crisis onset). See TH3
resolution and M01-08.

Constraints:
  - Requires an active IBKR market data subscription.
  - When IBKR data is unavailable, returns None — the caller falls back to
    FRED's daily HY OAS value.
  - IBKR_HOST and IBKR_PORT env vars configure the connection (defaults to
    localhost:7497 for TWS paper trading).
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class IBKRSpreadProxy:
    """Intraday HYG-IEF spread proxy for HY OAS estimation.

    Uses the IBKR API to fetch real-time prices for HYG (iShares iBoxx $
    High Yield Corporate Bond ETF) and IEF (iShares 7-10 Year Treasury Bond
    ETF). The spread ``HYG_price - IEF_price`` is a rough intraday proxy for
    credit spread direction when FRED's daily HY OAS is stale.

    This is NOT a precise spread measurement — it tracks directional moves
    in credit risk sentiment between FRED's daily publishes.
    """

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        self._host = host or os.environ.get("IBKR_HOST", "127.0.0.1")
        self._port = port or int(os.environ.get("IBKR_PORT", "7497"))

    async def is_available(self) -> bool:
        """Check whether the IBKR data subscription is reachable.

        Returns True if a TCP connection to the IBKR gateway can be
        established, False otherwise.
        """
        import asyncio

        logger.info(
            "ibkr.is_available.start",
            host=self._host,
            port=self._port,
        )
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=5.0,
            )
            writer.close()
            await writer.wait_closed()
            logger.info("ibkr.is_available.ok", available=True)
            return True
        except (OSError, asyncio.TimeoutError) as exc:
            logger.warning(
                "ibkr.is_available.unavailable",
                error=str(exc),
                host=self._host,
                port=self._port,
            )
            return False

    async def fetch_spread(self) -> dict[str, Any] | None:
        """Fetch the current HYG-IEF spread.

        Returns a dict with keys ``spread``, ``hyg_price``, ``ief_price``,
        and ``timestamp`` (ISO-8601). Returns ``None`` when IBKR data is
        unavailable — the caller should fall back to FRED daily HY OAS.
        """
        logger.info("ibkr.fetch_spread.start")
        t0 = time.monotonic()

        if not await self.is_available():
            logger.warning("ibkr.fetch_spread.unavailable", fallback="fred_daily")
            return None

        try:
            hyg_price = await self._fetch_last_price("HYG")
            ief_price = await self._fetch_last_price("IEF")

            if hyg_price is None or ief_price is None:
                logger.warning(
                    "ibkr.fetch_spread.missing_price",
                    hyg_price=hyg_price,
                    ief_price=ief_price,
                )
                return None

            spread = hyg_price - ief_price
            now = datetime.now(tz=timezone.utc)
            elapsed_ms = (time.monotonic() - t0) * 1000

            result: dict[str, Any] = {
                "spread": round(spread, 4),
                "hyg_price": round(hyg_price, 4),
                "ief_price": round(ief_price, 4),
                "timestamp": now.isoformat(),
            }

            logger.info(
                "ibkr.fetch_spread.ok",
                spread=result["spread"],
                hyg_price=result["hyg_price"],
                ief_price=result["ief_price"],
                elapsed_ms=round(elapsed_ms, 1),
            )
            return result

        except Exception as exc:
            logger.error(
                "ibkr.fetch_spread.error",
                error=str(exc),
            )
            return None

    async def _fetch_last_price(self, symbol: str) -> float | None:
        """Fetch the last traded price for *symbol* from IBKR.

        This is a placeholder integration point. A full implementation would
        use the ``ib_insync`` or ``ibapi`` library to request market data.
        The method returns None when the price cannot be obtained, triggering
        the FRED fallback in the caller.
        """
        # Full IBKR API integration requires ib_insync or ibapi.
        # Import lazily to avoid hard dependency.
        try:
            import ib_insync  # noqa: WPS433
        except ImportError:
            logger.warning(
                "ibkr._fetch_last_price.no_driver",
                symbol=symbol,
                hint="Install ib_insync: pip install ib_insync",
            )
            return None

        logger.info("ibkr._fetch_last_price.start", symbol=symbol)
        try:
            ib = ib_insync.IB()
            await ib.connectAsync(self._host, self._port, clientId=0)
            contract = ib_insync.Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)
            ticker = ib.reqMktData(contract, snapshot=True)
            # Wait briefly for the snapshot to arrive.
            import asyncio
            await asyncio.sleep(2)
            price = ticker.last if ticker.last == ticker.last else ticker.close
            ib.disconnect()
            logger.info(
                "ibkr._fetch_last_price.ok",
                symbol=symbol,
                price=price,
            )
            return float(price) if price is not None and price == price else None
        except Exception as exc:
            logger.error(
                "ibkr._fetch_last_price.error",
                symbol=symbol,
                error=str(exc),
            )
            return None
