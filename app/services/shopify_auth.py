"""
Shopify Dynamic Token Manager
==============================
Automatically fetches and refreshes the Shopify Admin API token using
the client_credentials OAuth grant. This avoids the need to manually
rotate SHOPIFY_ADMIN_TOKEN in the environment when it expires (~24h).

Usage:
    from app.services.shopify_auth import get_admin_token

    token = await get_admin_token()   # always returns a fresh, valid token
"""

import asyncio
import time
import httpx
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration (credentials stored in env; fallback to hardcoded defaults)
# ---------------------------------------------------------------------------
_SHOPIFY_OAUTH_URL = "https://tcg-nakama-2.myshopify.com/admin/oauth/access_token"
_CLIENT_ID = os.getenv("SHOPIFY_OAUTH_CLIENT_ID", "d1df73a5a46f7bc96fde49242f17f023")
_CLIENT_SECRET = os.getenv("SHOPIFY_OAUTH_CLIENT_SECRET", "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")

# Refresh the token this many seconds BEFORE it actually expires (safety buffer)
_REFRESH_BUFFER_SECONDS = 300  # 5 minutes


# ---------------------------------------------------------------------------
# In-memory token cache
# ---------------------------------------------------------------------------
class _TokenCache:
    def __init__(self):
        self._token: Optional[str] = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    def is_valid(self) -> bool:
        """Return True if we have a token that won't expire within the buffer."""
        return bool(self._token) and (time.monotonic() < self._expires_at - _REFRESH_BUFFER_SECONDS)

    async def fetch_new_token(self) -> str:
        """Call Shopify OAuth endpoint and cache the result."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _SHOPIFY_OAUTH_URL,
                json={
                    "grant_type": "client_credentials",
                    "client_id": _CLIENT_ID,
                    "client_secret": _CLIENT_SECRET,
                }
            )
            response.raise_for_status()
            data = response.json()

        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"[ShopifyAuth] No access_token in response: {data}")

        expires_in = int(data.get("expires_in", 86400))
        self._token = token
        self._expires_at = time.monotonic() + expires_in
        print(f"[ShopifyAuth] New token fetched. Expires in {expires_in}s "
              f"(prefix: {token[:12]}...)")
        return token

    async def get(self) -> str:
        """Return a valid token, fetching a new one if necessary."""
        if self.is_valid():
            return self._token  # type: ignore[return-value]

        async with self._lock:
            # Double-check inside the lock to avoid thundering herd
            if self.is_valid():
                return self._token  # type: ignore[return-value]
            return await self.fetch_new_token()


# ---------------------------------------------------------------------------
# Module-level singleton cache
# ---------------------------------------------------------------------------
_cache = _TokenCache()


async def get_admin_token() -> str:
    """
    Public API — returns a valid Shopify Admin API token.

    - On first call (or after expiry) it fetches a fresh token via OAuth.
    - Subsequent calls within the ~24-hour window return the cached token.
    - A 5-minute safety buffer ensures the token is never used right at expiry.

    Raises:
        RuntimeError: If the OAuth call fails or returns no token.
        httpx.HTTPStatusError: If the HTTP request itself fails.
    """
    return await _cache.get()


def get_admin_token_sync() -> Optional[str]:
    """
    Synchronous helper for contexts where you can't await.
    Falls back to env-var SHOPIFY_ADMIN_TOKEN if the cache is empty.
    Only use this as a last resort — prefer get_admin_token() everywhere.
    """
    if _cache.is_valid():
        return _cache._token
    # Fallback: try env var (legacy / manually set)
    return os.getenv("SHOPIFY_ADMIN_TOKEN")
