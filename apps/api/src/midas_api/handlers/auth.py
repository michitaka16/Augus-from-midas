"""
Auth handlers — signup, login, MFA, JWT (M07-02).

Password hashing: bcrypt. JWT: 15min access + 7d refresh.
MFA: TOTP (Google Authenticator compatible).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
_ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)
_REFRESH_TOKEN_EXPIRY = timedelta(days=7)


class AuthHandlers:
    """Authentication and user management handlers."""

    def __init__(self, conn: Any):
        self._conn = conn

    async def signup(self, email: str, password: str) -> dict:
        """POST /auth/signup — create account with hashed password."""
        logger.info("auth.signup.start", email=email)

        existing = await self._conn.fetchrow(
            "SELECT id FROM users.accounts WHERE email = $1", email
        )
        if existing:
            logger.warning("auth.signup.email_exists", email=email)
            return {"error": "Email already registered", "status": 409}

        password_hash = _hash_password(password)
        user_id = await self._conn.fetchval(
            """INSERT INTO users.accounts (email, password_hash)
               VALUES ($1, $2) RETURNING id""",
            email, password_hash,
        )

        # Create default preferences
        await self._conn.execute(
            """INSERT INTO users.preferences (user_id, model_portfolio_id, timeout_hours, paper_trading)
               VALUES ($1, 'growth', 24, TRUE)""",
            user_id,
        )

        logger.info("auth.signup.complete", user_id=user_id)
        return {"user_id": user_id, "status": 201}

    async def login(self, email: str, password: str, mfa_token: str | None = None) -> dict:
        """POST /auth/login — verify credentials, return JWT."""
        logger.info("auth.login.start", email=email)

        row = await self._conn.fetchrow(
            "SELECT id, password_hash, mfa_secret, mfa_enabled FROM users.accounts WHERE email = $1 AND is_active = TRUE",
            email,
        )
        if not row:
            logger.warning("auth.login.not_found", email=email)
            return {"error": "Invalid credentials", "status": 401}

        if not _verify_password(password, row["password_hash"]):
            logger.warning("auth.login.wrong_password", email=email)
            return {"error": "Invalid credentials", "status": 401}

        if row["mfa_enabled"]:
            if not mfa_token:
                return {"error": "MFA token required", "status": 401, "mfa_required": True}
            if not _verify_totp(row["mfa_secret"], mfa_token):
                logger.warning("auth.login.bad_mfa", email=email)
                return {"error": "Invalid MFA token", "status": 401}

        tokens = _generate_tokens(row["id"])
        logger.info("auth.login.ok", user_id=row["id"])
        return {"tokens": tokens, "user_id": row["id"], "status": 200}

    async def refresh(self, refresh_token: str) -> dict:
        """POST /auth/refresh — exchange refresh token for new access token."""
        claims = _decode_token(refresh_token)
        if not claims or claims.get("type") != "refresh":
            return {"error": "Invalid refresh token", "status": 401}

        tokens = _generate_tokens(claims["sub"])
        logger.info("auth.refresh.ok", user_id=claims["sub"])
        return {"tokens": tokens, "status": 200}

    async def mfa_setup(self, user_id: int) -> dict:
        """POST /auth/mfa/setup — generate TOTP secret for QR code."""
        import base64
        secret = base64.b32encode(secrets.token_bytes(20)).decode()

        await self._conn.execute(
            "UPDATE users.accounts SET mfa_secret = $1 WHERE id = $2",
            secret, user_id,
        )

        logger.info("auth.mfa_setup", user_id=user_id)
        return {
            "secret": secret,
            "otpauth_uri": f"otpauth://totp/Midas:{user_id}?secret={secret}&issuer=Midas",
            "status": 200,
        }

    async def mfa_verify(self, user_id: int, token: str) -> dict:
        """POST /auth/mfa/verify — verify TOTP and enable MFA."""
        row = await self._conn.fetchrow(
            "SELECT mfa_secret FROM users.accounts WHERE id = $1", user_id
        )
        if not row or not row["mfa_secret"]:
            return {"error": "MFA not set up", "status": 400}

        if not _verify_totp(row["mfa_secret"], token):
            return {"error": "Invalid token", "status": 400}

        await self._conn.execute(
            "UPDATE users.accounts SET mfa_enabled = TRUE WHERE id = $1", user_id
        )

        logger.info("auth.mfa_enabled", user_id=user_id)
        return {"mfa_enabled": True, "status": 200}


# ── Password Hashing ────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash password with bcrypt (lazy import)."""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        # Fallback: PBKDF2 (stdlib)
        salt = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return f"pbkdf2:{salt}:{h.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    try:
        import bcrypt
        if stored_hash.startswith("$2"):
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except ImportError:
        pass

    if stored_hash.startswith("pbkdf2:"):
        _, salt, expected = stored_hash.split(":")
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(h.hex(), expected)

    return False


# ── JWT ─────────────────────────────────────────────────────

def _generate_tokens(user_id: int) -> dict:
    """Generate access + refresh JWT tokens."""
    try:
        import jwt
    except ImportError:
        raise ImportError("pyjwt required. Install with: pip install pyjwt")

    now = datetime.utcnow()
    access = jwt.encode(
        {"sub": str(user_id), "type": "access", "exp": now + _ACCESS_TOKEN_EXPIRY, "iat": now},
        _JWT_SECRET, algorithm="HS256",
    )
    refresh = jwt.encode(
        {"sub": str(user_id), "type": "refresh", "exp": now + _REFRESH_TOKEN_EXPIRY, "iat": now},
        _JWT_SECRET, algorithm="HS256",
    )
    return {"access_token": access, "refresh_token": refresh}


def _decode_token(token: str) -> dict | None:
    """Decode and verify a JWT token."""
    try:
        import jwt
        return jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


# ── TOTP ────────────────────────────────────────────────────

def _verify_totp(secret: str, token: str) -> bool:
    """Verify a TOTP token (RFC 6238). Accepts ±1 time step."""
    import base64

    try:
        key = base64.b32decode(secret)
    except Exception:
        return False

    current_step = int(time.time()) // 30
    for offset in (-1, 0, 1):
        step = current_step + offset
        step_bytes = step.to_bytes(8, "big")
        h = hmac.new(key, step_bytes, hashlib.sha1).digest()
        offset_val = h[-1] & 0x0F
        code = ((h[offset_val] & 0x7F) << 24 | h[offset_val + 1] << 16 |
                h[offset_val + 2] << 8 | h[offset_val + 3]) % 1_000_000
        if str(code).zfill(6) == token:
            return True
    return False
