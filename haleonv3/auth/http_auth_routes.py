import uuid

from starlette.responses import PlainTextResponse, RedirectResponse

from haleonv3.auth.sso import SSO
from haleonv3.db.database import get_session, init_db
from haleonv3.db.crud.users import upsert_user_from_claims


sso = SSO()


def mount_http_auth_routes(app):
    """Mount simple SSO routes on the backend app."""

    @app.get("/auth/login")
    def auth_login():
        url, _state = sso.get_authorization_url()
        if not url:
            return PlainTextResponse("SSO error", status_code=500)
        return RedirectResponse(url)

    @app.get("/auth/callback")
    def auth_callback(code: str, state: str):
        if not sso.validate_state(state):
            return PlainTextResponse("Invalid state", status_code=400)

        sso.fetch_tokens(code)
        claims = sso.verify_id_token() or {}

        # Minimal claim mapping expected by our CRUD
        claims = {
            "immutable_id": claims.get("immutable_id"),
            "email": claims.get("email"),
            "first_name": claims.get("given_name"),
            "family_name": claims.get("family_name"),
            "country": claims.get("country"),
        }

        if not claims.get("immutable_id"):
            return PlainTextResponse("Missing immutable_id claim", status_code=400)

        init_db()
        request_id = str(uuid.uuid4())
        with next(get_session()) as session:
            upsert_user_from_claims(session, claims, request_id=request_id)

        return RedirectResponse("/")
