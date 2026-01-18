import uuid

from starlette.responses import PlainTextResponse, RedirectResponse, JSONResponse
from sqlmodel import select

from haleonv3.auth.sso import SSO
from haleonv3.db.database import get_session, init_db
from haleonv3.db.crud.users import upsert_user_from_claims
from haleonv3.db.model.users import Users


sso = SSO()


def auth_login(request):
    url, _state = sso.get_authorization_url()
    if not url:
        return PlainTextResponse("SSO error", status_code=500)
    return RedirectResponse(url)


def auth_callback(request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        return PlainTextResponse("Missing code/state", status_code=400)

    if not sso.validate_state(state):
        return PlainTextResponse("Invalid state", status_code=400)

    sso.fetch_tokens(code)
    claims = sso.verify_id_token() or {}

    if not claims.get("immutable_id"):
        return PlainTextResponse("Missing immutable_id claim", status_code=400)

    init_db()
    request_id = str(uuid.uuid4())
    with next(get_session()) as session:
        user = upsert_user_from_claims(session, claims, request_id=request_id)
        session_id = str(uuid.uuid4())
        user.session_id = session_id
        session.add(user)
        session.commit()

    response = RedirectResponse("http://localhost:3000/")
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


def auth_me(request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return PlainTextResponse("No session", status_code=401)

    with next(get_session()) as session:
        user = session.exec(
            select(Users).where(Users.session_id == session_id)
        ).first()
        if not user:
            return PlainTextResponse("Invalid session", status_code=401)

    return JSONResponse(
        {
            "immutable_id": user.immutable_id,
            "email": user.email,
            "given_name": user.given_name,
            "family_name": user.family_name,
            "country": user.country,
        }
    )


def mount_http_auth_routes(app):
    """Mount simple SSO routes on the backend app."""
    app.add_route("/auth/login", auth_login, methods=["GET"])
    app.add_route("/auth/callback", auth_callback, methods=["GET"])
    app.add_route("/auth/me", auth_me, methods=["GET"])
