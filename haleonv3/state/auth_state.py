import reflex as rx
from http.cookies import SimpleCookie
from sqlmodel import select

from haleonv3.db.database import get_session
from haleonv3.db.model.users import Users
from haleonv3.auth.permissions import UserPermissions


class AuthState(rx.State):
    """Minimal global auth state."""

    is_authenticated: bool = False
    immutable_id: str = ""
    email: str = ""
    given_name: str = ""
    family_name: str = ""
    country: str = ""
    is_active: bool = False
    is_validated: bool = False
    is_admin: bool = False

    def load_me(self):
        headers = (self.router_data or {}).get("headers") or {}
        cookie_header = headers.get("cookie") or ""
        if not cookie_header:
            return

        c = SimpleCookie()
        c.load(cookie_header)
        session_id = c.get("session_id").value if c.get("session_id") else None
        if not session_id:
            return

        with next(get_session()) as session:
            user = session.exec(
                select(Users).where(Users.session_id == session_id)
            ).first()
            if not user:
                return

        self.immutable_id = user.immutable_id or ""
        self.email = user.email or ""
        self.given_name = user.given_name or ""
        self.family_name = user.family_name or ""
        self.country = user.country or ""
        self.is_authenticated = True
        self.is_active = UserPermissions.is_active_user(user)
        self.is_validated = UserPermissions.is_validated_user(user)
        self.is_admin = UserPermissions.is_admin_user(user)

    def logout(self):
        self.is_authenticated = False
        self.immutable_id = ""
        self.email = ""
        self.given_name = ""
        self.family_name = ""
        self.country = ""
        self.is_active = False
        self.is_validated = False
        self.is_admin = False

    @rx.var
    def initials(self) -> str:
        g = (self.given_name or "").strip()
        f = (self.family_name or "").strip()
        if not g and not f:
            return "U"
        return (g[:1] + f[:1]).upper()
