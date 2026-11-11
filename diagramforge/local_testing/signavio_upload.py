"""Upload rendered diagrams to Signavio for visual verification."""

from __future__ import annotations

import json
import os
from pathlib import Path

from diagramforge.SETUP import forge_logger as log


def _load_env() -> None:
    """Load .env file into os.environ if not already set."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key not in os.environ:
                os.environ[key] = value


_pm_instance = None
_pm_auth = None  # type: ignore[var-annotated]
_last_saved_token: str | None = None


def _get_pm():
    """Return a cached ProcessManagerAPI instance.

    On first call, attempts to restore an authenticated session from
    ``~/.cache/diagramforge/signavio_session.json`` to avoid hitting Process
    Manager's ``/p/login`` endpoint (which counts toward an account-wide
    login-attempt limit). Falls back to a fresh credential login when no
    cached session exists; persists the result so the next run can reuse it.

    Cached tokens that have expired server-side are handled transparently
    by the SDK's ``auth_flow``: a 401 on any request triggers an automatic
    re-authentication using the stored credentials.
    """
    global _pm_instance, _pm_auth, _last_saved_token
    if _pm_instance is not None:
        return _pm_instance

    import httpx
    from signavio import CredentialAuthentication, Signavio
    from signavio.authentication import CLOUDOS_URLS

    from local_testing import signavio_session_cache as cache

    _load_env()

    username = os.getenv("SIGNAVIO_USERNAME")
    password = os.getenv("SIGNAVIO_PASSWORD")
    tenant_id = os.getenv("SIGNAVIO_TENANT_ID")
    base_url = CLOUDOS_URLS["production"]

    auth = CredentialAuthentication(
        username=username,
        password=password,
        cloud_os="production",
        tenant_id=tenant_id,
    )

    cached = cache.load_session(base_url=base_url, tenant_id=tenant_id, username=username or "")
    if cached:
        # Inject the previously obtained session into the fresh auth provider.
        # auth_flow() short-circuits the /p/login call when both fields are set;
        # if the cached token is stale, a 401 on the first real request will
        # trigger a transparent re-login via the SDK's built-in retry path.
        auth._auth_token = cached["auth_token"]
        auth._cookies = httpx.Cookies(cached.get("cookies", {}))
        _last_saved_token = cached["auth_token"]
        log.info(f"Reusing cached Signavio session ({cache.CACHE_FILE})")
    else:
        # No cache — perform an explicit login now so we can persist the result
        # before any business calls. authenticate() populates _auth_token/_cookies.
        auth.authenticate()
        cache.save_session(
            base_url=base_url,
            tenant_id=tenant_id,
            username=username or "",
            auth_token=auth._auth_token,
            cookies=auth._cookies,
        )
        _last_saved_token = auth._auth_token
        log.info("Authenticated to Signavio (session cached)")

    _pm_auth = auth
    _pm_instance = Signavio(auth).pm
    return _pm_instance


def upload_diagram(json_path: Path, name: str | None = None) -> str:
    """Upload a rendered diagram JSON to Signavio.

    Returns the model ID of the created diagram.
    """
    from signavio.authentication import CLOUDOS_URLS
    from signavio.pm.models import PMModelCreate

    from local_testing import signavio_session_cache as cache

    pm = _get_pm()
    directory_id = os.getenv("SIGNAVIO_TARGET_DIRECTORY_ID")

    with open(json_path) as f:
        diagram_json = json.load(f)

    diagram_name = name or json_path.stem

    # Build the EXACT json_xml string that we will send, then write it to disk
    # before the request fires. This guarantees the on-disk artifact and the
    # uploaded payload are byte-for-byte identical.
    json_xml = json.dumps(diagram_json)
    json_path.write_text(json_xml)
    log.info(f"Wrote uploaded payload to {json_path}")

    result = pm.model_create(
        model_data=PMModelCreate(
            name=diagram_name,
            parent=directory_id,
            json_xml=json_xml,
        )
    )

    # Re-persist the session ONLY if the SDK transparently re-authenticated
    # mid-call (a 401 in auth_flow rotates _auth_token in place). When the
    # token still matches what we already wrote, the on-disk copy is current
    # and we skip both the file write and the log line.
    global _last_saved_token
    if _pm_auth is not None:
        current_token = getattr(_pm_auth, "_auth_token", "") or ""
        if current_token and current_token != _last_saved_token:
            cache.save_session(
                base_url=CLOUDOS_URLS["production"],
                tenant_id=os.getenv("SIGNAVIO_TENANT_ID"),
                username=os.getenv("SIGNAVIO_USERNAME") or "",
                auth_token=current_token,
                cookies=_pm_auth._cookies,
            )
            _last_saved_token = current_token
            log.info("Signavio session token rotated; cache updated")

    model_id = getattr(result, "href", "").split("/")[-1] if hasattr(result, "href") else str(result)
    log.success(f"Uploaded '{diagram_name}' (model: {model_id})")
    return model_id
