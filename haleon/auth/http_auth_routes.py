"""Server-side auth routes (Starlette) for HttpOnly session cookies.

Reflex 0.8.x `rx.Cookie` is client-side storage (JS) so it cannot set HttpOnly.
These routes run on the backend (Starlette) and can set/clear HttpOnly cookies
via `Set-Cookie` headers.

Routes:
- GET /auth/login    : start OIDC auth (PKCE) and redirect to IdP
- GET /auth/callback : handle IdP redirect, verify token, issue app session cookie (HttpOnly)
- GET /auth/logout   : clear session in DB + clear HttpOnly cookie and redirect to /

NOTE: For production, store PKCE state in Redis (not in-process memory).
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response

from haleon.auth.sso import SSO
from haleon.db.database import get_session
from haleon.db.crud.users import (
    create_user,
    get_user_by_email,
    login_user,
    logout_user,
    update_user,
)


COOKIE_NAME = "session_id"
COOKIE_PATH = "/"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()

# In production behind HTTPS, set SECURE=true to emit Secure cookies.
# Default is True (secure-by-default). For local HTTP dev, override with COOKIE_SECURE=false.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").strip().lower() in ("true", "1", "yes")

# Environment (dev/prod). We keep safe defaults for local dev.
ENV = os.getenv("ENV", "dev").strip().lower()

# Where to send the browser after backend auth endpoints.
# In dev, Reflex runs frontend on :3000 and backend on :8000.
# In prod, you typically serve both on the same origin.
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")

# Pending PKCE store: state -> (code_verifier, created_at_epoch_seconds)
_PENDING: Dict[str, Tuple[str, float]] = {}
_PENDING_TTL_SECONDS = int(os.getenv("SSO_STATE_TTL_SECONDS", "600"))  # 10 minutes

# Optional Redis backing for PKCE state (recommended in prod/multi-instance).
_REDIS_URL = os.getenv("REDIS_URL", "").strip()
_REDIS = None
if _REDIS_URL:
    try:
        import redis  # type: ignore

        _REDIS = redis.Redis.from_url(_REDIS_URL, decode_responses=True)
    except Exception:
        _REDIS = None


def _pkce_key(state: str) -> str:
    return f"haleon:sso_state:{state}"


def _pending_set(state: str, code_verifier: str) -> None:
    if _REDIS is not None:
        # Store as plain verifier; TTL enforces expiration.
        _REDIS.setex(_pkce_key(state), _PENDING_TTL_SECONDS, code_verifier)
        return
    _PENDING[state] = (code_verifier, time.time())


def _pending_pop(state: str) -> Optional[str]:
    if _REDIS is not None:
        key = _pkce_key(state)
        val = _REDIS.get(key)
        if val:
            _REDIS.delete(key)
            return val
        return None
    pending = _PENDING.pop(state, None)
    if not pending:
        return None
    code_verifier, _ts = pending
    return code_verifier


def _prune_pending() -> None:
    if _REDIS is not None:
        # Redis handles TTL.
        return
    now = time.time()
    expired = [k for k, (_, ts) in _PENDING.items() if now - ts > _PENDING_TTL_SECONDS]
    for k in expired:
        _PENDING.pop(k, None)


def _extract_country_from_claims(claims: dict) -> str:
    # Customer payload: {"adress": {"country": "CH"}} (yes, "adress")
    addr = claims.get("adress") or claims.get("address") or {}
    if isinstance(addr, dict):
        return (addr.get("country") or "").strip()
    return ""

def _require_csrf_same_origin(request: Request) -> Optional[Response]:
    """Basic CSRF protection for state-changing routes (prod only).

    For browser navigations, Origin may be absent; Referer is usually present.
    We accept if either Origin equals FRONTEND_BASE_URL or Referer starts with FRONTEND_BASE_URL.
    """
    if ENV != "prod":
        return None
    origin = (request.headers.get("origin") or "").rstrip("/")
    referer = (request.headers.get("referer") or "").strip()
    if origin and origin == FRONTEND_BASE_URL:
        return None
    if referer and referer.startswith(FRONTEND_BASE_URL):
        return None
    return PlainTextResponse("CSRF blocked", status_code=403)


async def auth_login(request: Request) -> Response:
    """Start SSO login (PKCE) and redirect to the IdP."""
    _prune_pending()

    # Ensure redirect URI is backend callback (this endpoint on backend origin).
    backend_base = str(request.base_url).rstrip("/")
    os.environ["REDIRECT_URI"] = f"{backend_base}/auth/callback"

    sso = SSO()
    # If SSO is not configured (no .env / missing env vars), fall back to dev login.
    if not (sso.auth_url and sso.client_id and sso.token_url and sso.jwks_url and sso.issuer):
        if ENV == "dev":
            return RedirectResponse(f"{backend_base}/auth/dev-login", status_code=302)
        return PlainTextResponse("SSO not configured", status_code=500)

    auth_url, state = sso.get_authorization_url()
    if not auth_url or not state or not sso.code_verifier:
        # Defensive fallback (still allow app to work without SSO config) in dev.
        if ENV == "dev":
            return RedirectResponse(f"{backend_base}/auth/dev-login", status_code=302)
        return PlainTextResponse("SSO start failed", status_code=500)

    _pending_set(state, sso.code_verifier)
    return RedirectResponse(auth_url, status_code=302)


async def auth_callback(request: Request) -> Response:
    """Finish SSO login, issue HttpOnly session cookie, redirect to /home."""
    _prune_pending()

    code = request.query_params.get("code", "")
    returned_state = request.query_params.get("state", "")
    if not code or not returned_state:
        return PlainTextResponse("Invalid SSO callback (missing code/state)", status_code=400)

    code_verifier = _pending_pop(returned_state)
    if not code_verifier:
        return PlainTextResponse("Invalid SSO callback (unknown/expired state)", status_code=400)

    # Ensure redirect URI matches the one used during /auth/login.
    backend_base = str(request.base_url).rstrip("/")
    os.environ["REDIRECT_URI"] = f"{backend_base}/auth/callback"

    sso = SSO()
    sso.state = returned_state
    sso.code_verifier = code_verifier

    token = sso.fetch_tokens(code)
    if not token:
        return PlainTextResponse("SSO token exchange failed", status_code=401)

    claims = sso.verify_id_token()
    if not claims:
        return PlainTextResponse("SSO id_token verification failed", status_code=401)

    email = (sso.email or "").strip()
    first_name = (sso.first_name or "").strip()
    family_name = (sso.family_name or "").strip()
    country = _extract_country_from_claims(claims)

    if not email:
        return PlainTextResponse("SSO claims missing email", status_code=400)

    # Issue app session id and persist in DB.
    session_id = str(uuid.uuid4())
    session = next(get_session())
    try:
        user = get_user_by_email(session, email)
        if user:
            user = update_user(
                session=session,
                user=user,
                family_name=family_name or None,
                first_name=first_name or None,
                country=country or None,
                audit_user=None,
                audit_source="auth/sso",
            )
            user = login_user(session=session, user=user, session_id=session_id, audit_user=None, audit_source="auth/sso")
        else:
            user = create_user(
                session=session,
                email=email,
                family_name=family_name or None,
                first_name=first_name or None,
                country=country or None,
                is_admin=False,
                is_connected=False,
                audit_user=None,
                audit_source="auth/sso",
            )
            user = login_user(session=session, user=user, session_id=session_id, audit_user=None, audit_source="auth/sso")
    finally:
        session.close()

    resp = RedirectResponse(f"{FRONTEND_BASE_URL}/home", status_code=302)
    resp.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=60 * 60,  # 1 hour (align with AuthState.session_duration)
    )
    return resp


async def auth_logout(request: Request) -> Response:
    """Clear DB session and clear HttpOnly cookie."""
    blocked = _require_csrf_same_origin(request)
    if blocked:
        return blocked
    sid = request.cookies.get(COOKIE_NAME) or ""

    if sid:
        session = next(get_session())
        try:
            from haleon.db.crud.users import get_user_by_session_id

            user = get_user_by_session_id(session, sid)
            if user:
                logout_user(session=session, user=user, audit_user=None, audit_source="auth/logout")
        finally:
            session.close()

    resp = RedirectResponse(f"{FRONTEND_BASE_URL}/", status_code=302)
    resp.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH)
    return resp


async def auth_dev_login(request: Request) -> Response:
    """DEV ONLY: issue an HttpOnly session cookie for the dummy user (John Doe)."""
    if ENV != "dev":
        return PlainTextResponse("Not found", status_code=404)
    # Dummy user profile
    email = "john.doe@haleon.com"
    first_name = "John"
    family_name = "Doe"
    country = "FR"

    # Issue app session id and persist in DB.
    session_id = str(uuid.uuid4())
    session = next(get_session())
    try:
        user = get_user_by_email(session, email)
        if user:
            user = update_user(
                session=session,
                user=user,
                family_name=family_name,
                first_name=first_name,
                country=country,
                audit_user=None,
                audit_source="auth/dev-login",
            )
            user = login_user(session=session, user=user, session_id=session_id, audit_user=None, audit_source="auth/dev-login")
        else:
            user = create_user(
                session=session,
                email=email,
                family_name=family_name,
                first_name=first_name,
                country=country,
                is_admin=False,
                is_connected=False,
                audit_user=None,
                audit_source="auth/dev-login",
            )
            user = login_user(session=session, user=user, session_id=session_id, audit_user=None, audit_source="auth/dev-login")
    finally:
        session.close()

    resp = RedirectResponse(f"{FRONTEND_BASE_URL}/home", status_code=302)
    resp.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=60 * 60,
    )
    return resp


async def auth_health(_request: Request) -> Response:
    """Minimal endpoint to confirm backend auth routes are mounted."""
    return JSONResponse({"ok": True, "cookie_secure": COOKIE_SECURE})

async def backend_root(_request: Request) -> Response:
    """Friendly root for the backend: redirect to the frontend."""
    return RedirectResponse(f"{FRONTEND_BASE_URL}/", status_code=302)


def mount_http_auth_routes(app: Starlette) -> None:
    """Mount auth routes on the Reflex backend Starlette app."""
    app.add_route("/", backend_root, methods=["GET"])
    app.add_route("/auth/login", auth_login, methods=["GET"])
    app.add_route("/auth/callback", auth_callback, methods=["GET"])
    app.add_route("/auth/dev-login", auth_dev_login, methods=["GET"])
    app.add_route("/auth/logout", auth_logout, methods=["GET"])
    app.add_route("/auth/health", auth_health, methods=["GET"])


