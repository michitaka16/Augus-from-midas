"""
Midas API server entry point.

Usage:
    uv run python -m midas_api

Starts the API server with all handlers mounted.
Runs boot-time governance assertions before accepting traffic.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

import structlog

logger = structlog.get_logger(__name__)


async def startup() -> None:
    """Initialize all services and run governance assertions."""
    try:
        import asyncpg
    except ImportError:
        logger.error("startup.missing_asyncpg", hint="pip install asyncpg")
        sys.exit(1)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("startup.no_database_url", hint="Set DATABASE_URL in .env")
        sys.exit(1)

    logger.info("startup.connecting", database=database_url.split("@")[-1])
    conn = await asyncpg.connect(database_url)

    # 1. Run governance assertions (ADR-009, M06-05)
    # If ANY assertion fails, the API refuses to start.
    try:
        from midas_governance.assertions import run_all_assertions
        await run_all_assertions(conn)
        logger.info("startup.governance_passed")
    except Exception as e:
        logger.critical("startup.governance_FAILED", error=str(e))
        logger.critical(
            "startup.blocked",
            reason="Governance assertions failed. Fix the grants before starting the API.",
        )
        await conn.close()
        sys.exit(1)

    # 2. Initialize data fabric
    from midas_data.fabric import DataFabric
    fabric = DataFabric(database_url=database_url)
    await fabric.initialize()
    logger.info("startup.fabric_initialized")

    # 3. Initialize audit trail
    from midas_governance.audit import AuditTrail
    audit = AuditTrail(conn)
    logger.info("startup.audit_initialized")

    # 4. Initialize debate agent with tools
    from midas_debate.agent.debate import DebateAgent
    from midas_debate.tools.data_tools import DebateTools
    tools = DebateTools(fabric)
    debate_agent = DebateAgent(tools=tools.as_dict())
    logger.info("startup.debate_agent_initialized")

    # 5. Initialize API gateway
    from midas_api.channels import MidasAPI
    api = MidasAPI(conn, audit_trail=audit)
    api.debate = type(api.debate)(conn, debate_agent=debate_agent)
    logger.info("startup.api_initialized", routes=len(api.ROUTES))

    # 6. Start HTTP server
    await run_server(api, conn, fabric)


async def run_server(api: object, conn: object, fabric: object) -> None:
    """Run the HTTP server. Uses a simple asyncio-based server for v1.

    In production, this would be mounted on Nexus or uvicorn+FastAPI.
    For development, we use a lightweight ASGI approach.
    """
    port = int(os.environ.get("PORT", "8000"))
    logger.info("server.starting", port=port)

    try:
        # For development: simple HTTP server using aiohttp
        try:
            from aiohttp import web

            app = web.Application()

            # Mount signal routes (no auth — impersonal publisher)
            app.router.add_get("/signals/latest", _wrap(api.signals.get_latest_all))
            app.router.add_get("/signals/{portfolio_id}/latest",
                              _wrap_param(api.signals.get_latest_portfolio, "portfolio_id"))
            app.router.add_get("/signals/{portfolio_id}/history",
                              _wrap_param(api.signals.get_history, "portfolio_id"))

            # Mount regime routes (no auth)
            app.router.add_get("/regime/current", _wrap(api.regime.get_current))
            app.router.add_get("/regime/history", _wrap(api.regime.get_history))

            # Mount backtest routes (no auth)
            app.router.add_get("/backtests/{portfolio_id}/latest",
                              _wrap_param(api.backtests.get_latest, "portfolio_id"))

            # Mount backtest run by ID (no auth — for citation links)
            async def get_backtest_run(request: web.Request) -> web.Response:
                run_id = int(request.match_info["run_id"])
                result = await api.backtests.get_run(run_id)
                if not result:
                    return web.json_response({"error": "Not found"}, status=404)
                return web.json_response(result)
            app.router.add_get("/backtests/run/{run_id}", get_backtest_run)

            # ── Auth routes (no JWT required) ──────────────────
            async def signup(request: web.Request) -> web.Response:
                body = await request.json()
                result = await api.auth.signup(body["email"], body["password"])
                return web.json_response(result, status=result.get("status", 200))
            app.router.add_post("/auth/signup", signup)

            async def login(request: web.Request) -> web.Response:
                body = await request.json()
                result = await api.auth.login(
                    body["email"], body["password"], body.get("mfa_token")
                )
                return web.json_response(result, status=result.get("status", 200))
            app.router.add_post("/auth/login", login)

            async def refresh(request: web.Request) -> web.Response:
                body = await request.json()
                result = await api.auth.refresh(body["refresh_token"])
                return web.json_response(result, status=result.get("status", 200))
            app.router.add_post("/auth/refresh", refresh)

            # ── JWT-protected routes ───────────────────────────
            async def get_account(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                result = await api.account.get_profile(user_id)
                return web.json_response(result)
            app.router.add_get("/account", get_account)

            async def update_portfolio(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                body = await request.json()
                result = await api.account.update_portfolio(user_id, body["model_portfolio_id"])
                return web.json_response(result)
            app.router.add_put("/account/portfolio", update_portfolio)

            async def update_preferences(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                body = await request.json()
                result = await api.account.update_preferences(user_id, body)
                return web.json_response(result)
            app.router.add_put("/account/preferences", update_preferences)

            async def link_ibkr(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                result = await api.account.link_ibkr(user_id)
                return web.json_response(result)
            app.router.add_post("/account/ibkr/link", link_ibkr)

            async def unlink_ibkr(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                result = await api.account.unlink_ibkr(user_id)
                return web.json_response(result)
            app.router.add_delete("/account/ibkr/unlink", unlink_ibkr)

            async def get_pending(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                result = await api.approvals.get_pending(user_id)
                return web.json_response(result)
            app.router.add_get("/approvals/pending", get_pending)

            async def approve(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                approval_id = int(request.match_info["approval_id"])
                result = await api.approvals.approve(user_id, approval_id)
                return web.json_response(result)
            app.router.add_post("/approvals/{approval_id}/approve", approve)

            async def reject(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                approval_id = int(request.match_info["approval_id"])
                result = await api.approvals.reject(user_id, approval_id)
                return web.json_response(result)
            app.router.add_post("/approvals/{approval_id}/reject", reject)

            async def hold(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                approval_id = int(request.match_info["approval_id"])
                result = await api.approvals.hold(user_id, approval_id)
                return web.json_response(result)
            app.router.add_post("/approvals/{approval_id}/hold", hold)

            async def approval_history(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                result = await api.approvals.get_history(user_id)
                return web.json_response(result)
            app.router.add_get("/approvals/history", approval_history)

            async def debate_message(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                body = await request.json()
                result = await api.debate.send_message(user_id, body["message"])
                return web.json_response(result)
            app.router.add_post("/debate/message", debate_message)

            async def debate_history(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                result = await api.debate.get_history(user_id)
                return web.json_response(result)
            app.router.add_get("/debate/history", debate_history)

            async def strategy_health(request: web.Request) -> web.Response:
                portfolio_id = request.match_info["portfolio_id"]
                result = await api.regime.get_strategy_health(portfolio_id)
                return web.json_response(result)
            app.router.add_get("/health/strategy/{portfolio_id}", strategy_health)

            # ── Audit trail (auth required) ────────────────────
            async def audit_trail(request: web.Request) -> web.Response:
                user_id = _extract_user(request)
                if not user_id:
                    return web.json_response({"error": "Unauthorized"}, status=401)
                from midas_governance.audit import AuditTrail
                at = AuditTrail(api.approvals._conn)
                limit = int(request.query.get("limit", "50"))
                event_type = request.query.get("event_type")
                result = await at.get_recent(limit=limit, event_type=event_type)
                return web.json_response({"entries": result})
            app.router.add_get("/audit/trail", audit_trail)

            # ── CORS middleware ────────────────────────────────
            @web.middleware
            async def cors_middleware(request: web.Request, handler):
                if request.method == "OPTIONS":
                    resp = web.Response()
                else:
                    resp = await handler(request)
                resp.headers["Access-Control-Allow-Origin"] = "*"
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                return resp
            app.middlewares.append(cors_middleware)

            # Health check
            async def health(request: web.Request) -> web.Response:
                return web.json_response({"status": "ok"})
            app.router.add_get("/health", health)

            logger.info("server.ready", port=port, routes=len(app.router.routes()))
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", port)
            await site.start()
            logger.info("server.listening", port=port)

            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(3600)
            finally:
                await runner.cleanup()

        except ImportError:
            logger.warning("server.aiohttp_not_installed", hint="pip install aiohttp")
            logger.info("server.standing_by", port=port)
            # Keep the process alive for development
            while True:
                await asyncio.sleep(3600)

    except KeyboardInterrupt:
        logger.info("server.shutting_down")
    finally:
        await fabric.close()
        await conn.close()
        logger.info("server.stopped")


def _extract_user(request) -> int | None:
    """Extract user_id from JWT Authorization header. Returns None if invalid."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        import jwt
        claims = jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        if claims.get("type") != "access":
            return None
        return int(claims["sub"])
    except Exception:
        return None


_JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")


def _wrap(handler):
    """Wrap an async handler for aiohttp."""
    from aiohttp import web

    async def wrapped(request: web.Request) -> web.Response:
        try:
            result = await handler()
            cache = result.pop("_cache", None) if isinstance(result, dict) else None
            resp = web.json_response(result)
            if cache:
                for k, v in cache.items():
                    resp.headers[k] = v
            return resp
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    return wrapped


def _wrap_param(handler, param_name: str):
    """Wrap a handler that takes a path parameter."""
    from aiohttp import web

    async def wrapped(request: web.Request) -> web.Response:
        try:
            param = request.match_info[param_name]
            result = await handler(param)
            if result is None:
                return web.json_response({"error": "Not found"}, status=404)
            cache = result.pop("_cache", None) if isinstance(result, dict) else None
            resp = web.json_response(result)
            if cache:
                for k, v in cache.items():
                    resp.headers[k] = v
            return resp
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    return wrapped


def main() -> None:
    """Entry point."""
    asyncio.run(startup())


if __name__ == "__main__":
    main()
