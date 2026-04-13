"""
Midas DataFlow models — single source of truth for all database tables.

Schema design principles:
- `signals` table has NO user_id column (publisher exemption, ADR-001)
- User tables live in a separate schema
- Token storage uses BYTEA for encrypted tokens (ADR-013)
- Audit trail is append-only with chain hashing (ADR-014)
"""

from midas_data.models.market import Bar, Fundamental, CorpAction, EtfUniverse
from midas_data.models.signals import RegimeSignal, Signal, SignalInput, BacktestRun
from midas_data.models.news import NewsItem
from midas_data.models.users import User, UserPreference, UserToken, Approval
from midas_data.models.audit import AuditTrail
from midas_data.models.portfolios import ModelPortfolio

__all__ = [
    "Bar",
    "Fundamental",
    "CorpAction",
    "EtfUniverse",
    "RegimeSignal",
    "Signal",
    "SignalInput",
    "BacktestRun",
    "NewsItem",
    "User",
    "UserPreference",
    "UserToken",
    "Approval",
    "AuditTrail",
    "ModelPortfolio",
]
