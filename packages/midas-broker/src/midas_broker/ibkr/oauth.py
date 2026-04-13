"""
IBKR OAuth 2.0 flow (M05-02, ADR-013).

Token storage: AES-256-GCM encrypted in user_tokens table.
Scope minimization: read_positions + preview_order + place_order only.
Refresh token rotation: single-use, old invalidated on refresh.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

_OAUTH_SCOPES = "read_positions preview_order place_order"


class TokenEncryption:
    """AES-256-GCM encryption for OAuth tokens (ADR-013).

    Key from IBKR_TOKEN_ENCRYPTION_KEY env var. Never stored in DB.
    Token columns are BYTEA to prevent accidental logging.
    """

    def __init__(self):
        key_hex = os.environ.get("IBKR_TOKEN_ENCRYPTION_KEY", "")
        if not key_hex:
            raise ValueError(
                "IBKR_TOKEN_ENCRYPTION_KEY must be set in .env "
                "(32-byte hex string for AES-256)"
            )
        self._key = bytes.fromhex(key_hex)
        if len(self._key) != 32:
            raise ValueError("IBKR_TOKEN_ENCRYPTION_KEY must be 32 bytes (64 hex chars)")

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a token string to bytes (AES-256-GCM)."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import os as _os

        nonce = _os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return nonce + ciphertext

    def decrypt(self, data: bytes) -> str:
        """Decrypt bytes back to a token string."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()


class IBKROAuth:
    """IBKR OAuth 2.0 authorization code flow."""

    def __init__(self, conn: Any):
        self._conn = conn
        self._client_id = os.environ.get("IBKR_CLIENT_ID", "")
        self._client_secret = os.environ.get("IBKR_CLIENT_SECRET", "")
        self._redirect_uri = os.environ.get("IBKR_REDIRECT_URI", "")
        self._encryption = TokenEncryption()

    def get_authorization_url(self, state: str) -> str:
        """Generate the OAuth authorization URL for user redirect."""
        return (
            f"https://www.interactivebrokers.com/authorize"
            f"?response_type=code"
            f"&client_id={self._client_id}"
            f"&redirect_uri={self._redirect_uri}"
            f"&scope={_OAUTH_SCOPES}"
            f"&state={state}"
        )

    async def exchange_code(self, code: str, user_id: int) -> dict:
        """Exchange authorization code for access + refresh tokens."""
        async with httpx.AsyncClient() as client:
            logger.info("oauth.exchange.start", user_id=user_id)
            resp = await client.post(
                "https://www.interactivebrokers.com/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                },
            )

            if resp.status_code != 200:
                logger.error("oauth.exchange.failed", status=resp.status_code)
                raise ValueError(f"OAuth exchange failed: {resp.status_code}")

            tokens = resp.json()
            await self._store_tokens(user_id, tokens)
            logger.info("oauth.exchange.complete", user_id=user_id)
            return {"status": "linked"}

    async def refresh_tokens(self, user_id: int) -> str | None:
        """Refresh the access token. Returns new access token or None on failure.

        Single-use refresh: old refresh token invalidated on use.
        """
        stored = await self._get_stored_tokens(user_id)
        if not stored:
            return None

        refresh_token = self._encryption.decrypt(stored["refresh_token_enc"])

        async with httpx.AsyncClient() as client:
            logger.info("oauth.refresh.start", user_id=user_id)
            resp = await client.post(
                "https://www.interactivebrokers.com/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )

            if resp.status_code != 200:
                logger.warning("oauth.refresh.failed", user_id=user_id, status=resp.status_code)
                return None

            tokens = resp.json()
            await self._store_tokens(user_id, tokens)
            logger.info("oauth.refresh.complete", user_id=user_id)
            return tokens.get("access_token")

    async def get_access_token(self, user_id: int) -> str | None:
        """Get a valid access token, refreshing if needed."""
        stored = await self._get_stored_tokens(user_id)
        if not stored:
            return None

        if stored["expires_at"] and stored["expires_at"] < datetime.utcnow() + timedelta(minutes=5):
            return await self.refresh_tokens(user_id)

        return self._encryption.decrypt(stored["access_token_enc"])

    async def revoke(self, user_id: int) -> None:
        """Revoke tokens and delete from storage."""
        await self._conn.execute(
            "DELETE FROM tokens.user_tokens WHERE user_id = $1", user_id
        )
        logger.info("oauth.revoked", user_id=user_id)

    async def _store_tokens(self, user_id: int, tokens: dict) -> None:
        """Encrypt and store tokens in user_tokens table."""
        access_enc = self._encryption.encrypt(tokens["access_token"])
        refresh_enc = self._encryption.encrypt(tokens["refresh_token"])
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        await self._conn.execute(
            """INSERT INTO tokens.user_tokens (user_id, access_token_enc, refresh_token_enc, expires_at, updated_at)
               VALUES ($1, $2, $3, $4, NOW())
               ON CONFLICT (user_id)
               DO UPDATE SET access_token_enc = $2, refresh_token_enc = $3, expires_at = $4, updated_at = NOW()""",
            user_id, access_enc, refresh_enc, expires_at,
        )

    async def _get_stored_tokens(self, user_id: int) -> dict | None:
        """Fetch encrypted tokens from storage."""
        row = await self._conn.fetchrow(
            "SELECT access_token_enc, refresh_token_enc, expires_at FROM tokens.user_tokens WHERE user_id = $1",
            user_id,
        )
        return dict(row) if row else None
