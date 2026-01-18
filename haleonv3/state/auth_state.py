import reflex as rx


class AuthState(rx.State):
    """Minimal global auth state."""

    is_authenticated: bool = False
    immutable_id: str = ""
    email: str = ""
    given_name: str = ""
    family_name: str = ""
    country: str = ""

    def load_from_claims(self, claims: dict):
        self.immutable_id = claims.get("immutable_id", "")
        self.email = claims.get("email", "")
        self.given_name = claims.get("given_name", "")
        self.family_name = claims.get("family_name", "")
        self.country = claims.get("country", "")
        self.is_authenticated = True

    def logout(self):
        self.is_authenticated = False
        self.immutable_id = ""
        self.email = ""
        self.given_name = ""
        self.family_name = ""
        self.country = ""

    @rx.var
    def initials(self) -> str:
        g = (self.given_name or "").strip()
        f = (self.family_name or "").strip()
        if not g and not f:
            return "U"
        return (g[:1] + f[:1]).upper()
