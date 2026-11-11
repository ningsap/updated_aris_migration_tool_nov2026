"""Cross-run cache for Signavio Process Manager session credentials.

Each ``CredentialAuthentication`` instance, after a successful POST to
``/p/login``, holds two pieces of state:

* ``_auth_token`` — opaque string sent as the ``X-Signavio-Id`` header.
* ``_cookies``    — ``httpx.Cookies`` jar set by the same response.

Together they *are* the authenticated session. Persisting them to disk
lets us skip the login round-trip on subsequent runs, which avoids the
``login.attemptsExceeded`` lockout that Process Manager enforces on
repeated credential logins.

The cache file lives outside the repo at
``~/.cache/diagramforge/signavio_session.json`` and is keyed on
``(base_url, tenant_id, username)`` — switching any of those invalidates
the cache automatically. The token is opaque (not a JWT), so we cannot
introspect its expiry; instead we lean on the SDK's built-in behaviour:
if a cached token is stale, the next request will 401 and
``CredentialAuthentication.auth_flow`` re-authenticates transparently.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from diagramforge.SETUP import forge_logger as log

CACHE_DIR = Path.home() / ".cache" / "diagramforge"
CACHE_FILE = CACHE_DIR / "signavio_session.json"
CACHE_VERSION = 1


def _matches(cached: dict[str, Any], base_url: str, tenant_id: str | None, username: str) -> bool:
    return (
        cached.get("version") == CACHE_VERSION
        and cached.get("base_url") == base_url
        and cached.get("tenant_id") == tenant_id
        and cached.get("username") == username
    )


def load_session(base_url: str, tenant_id: str | None, username: str) -> dict[str, Any] | None:
    """Return the cached session payload, or None if missing/mismatched/corrupt."""
    if not CACHE_FILE.exists():
        return None

    try:
        cached = json.loads(CACHE_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(f"Session cache unreadable, ignoring: {exc}")
        return None

    if not _matches(cached, base_url, tenant_id, username):
        log.debug("Session cache does not match current credentials; ignoring")
        return None

    return cached


def save_session(
    *,
    base_url: str,
    tenant_id: str | None,
    username: str,
    auth_token: str,
    cookies: httpx.Cookies,
) -> None:
    """Persist a successful login's session token + cookies to disk."""
    payload = {
        "version": CACHE_VERSION,
        "base_url": base_url,
        "tenant_id": tenant_id,
        "username": username,
        "auth_token": auth_token,
        "cookies": {k: v for k, v in cookies.items()},
        "saved_at": time.time(),
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CACHE_DIR, 0o700)
    except OSError:
        pass

    tmp = CACHE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(CACHE_FILE)
    log.debug(f"Saved Signavio session cache to {CACHE_FILE}")


def clear_session() -> None:
    """Delete the cache file. Safe to call when the file does not exist."""
    try:
        CACHE_FILE.unlink()
        log.debug("Cleared Signavio session cache")
    except FileNotFoundError:
        pass
