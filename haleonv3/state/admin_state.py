import reflex as rx
from sqlmodel import select

from haleonv3.db.database import get_session
from haleonv3.db.crud.users import update_user_flags
from haleonv3.db.crud.user_role import grant_role, revoke_role
from haleonv3.db.model.users import Users
from haleonv3.db.model.user_role import UserRole
from haleonv3.db.crud.vendors import create_vendor, list_vendors, toggle_vendor_active
from haleonv3.state.auth_state import AuthState


class AdminState(AuthState):
    is_loading: bool = False
    users: list[dict] = []
    search_query: str = ""
    sort_value: str = "email"
    is_loading_vendors: bool = False
    vendors: list[dict] = []
    vendor_search: str = ""
    portfolio_filter: str = ""
    include_inactive: bool = True
    new_vendor_code: str = ""
    new_vendor_description: str = ""
    new_vendor_portfolio: str = ""

    # Roles (per app) - merged from RolesState for simplicity
    is_loading_roles: bool = False
    # Keep this beginner-simple: list apps manually.
    apps: list[str] = ["oob"]
    roles: list[dict] = []
    user_search: str = ""
    selected_user_id: int | None = None
    selected_app: str = ""

    @rx.event(background=True)
    async def load_users(self):
        async with self:
            self.is_loading = True

        with get_session() as session:
            rows = session.exec(select(Users)).all()

        async with self:
            self.users = [
                {
                    "id": u.id,
                    "immutable_id": u.immutable_id,
                    "email": u.email or "",
                    "given_name": u.given_name or "",
                    "family_name": u.family_name or "",
                    "is_active": bool(u.is_active),
                    "is_validated": bool(u.is_validated),
                    "is_admin": bool(u.is_admin),
                    "source_domain": int(getattr(u, "source_domain", 0)),
                }
                for u in rows
            ]
            self.is_loading = False

    @rx.event(background=True)
    async def load_roles(self):
        async with self:
            self.is_loading_roles = True

        with get_session() as session:
            rows = session.exec(
                select(UserRole, Users).where(UserRole.user_id == Users.id)
            ).all()

        async with self:
            self.roles = [
                {
                    "id": role.id,
                    "app": role.app,
                    "role": role.role,
                    "user_id": role.user_id,
                    "user_email": user.email or "",
                }
                for role, user in rows
            ]
            self.is_loading_roles = False

    def set_search_query(self, value: str):
        self.search_query = value or ""

    def set_sort_value(self, value: str):
        self.sort_value = value or "email"

    def set_vendor_search(self, value: str):
        self.vendor_search = value or ""

    def set_new_vendor_code(self, value: str):
        self.new_vendor_code = value or ""

    def set_new_vendor_description(self, value: str):
        self.new_vendor_description = value or ""

    def set_new_vendor_portfolio(self, value: str):
        self.new_vendor_portfolio = value or ""

    def set_portfolio_filter(self, value: str):
        self.portfolio_filter = value or ""

    def set_include_inactive(self, value: bool):
        self.include_inactive = bool(value)

    # --- Roles helpers (same names as old RolesState to keep UI simple) ---
    def set_user_search(self, value: str):
        self.user_search = value or ""

    def set_selected_user(self, value: str):
        try:
            self.selected_user_id = int(value)
        except (TypeError, ValueError):
            self.selected_user_id = None

    def set_selected_app(self, value: str):
        self.selected_app = value or ""

    @rx.var
    def user_options(self) -> list[dict]:
        return [{"label": user["email"], "value": user["id"]} for user in self.users]

    def grant_selected_moderator(self):
        if not self.selected_user_id:
            return rx.toast.error("Sélectionne un utilisateur.")
        if not self.selected_app:
            return rx.toast.error("Sélectionne une application.")
        return self.grant_app_moderator(self.selected_app, self.selected_user_id)

    def grant_app_moderator(self, app: str, user_id: int):
        if not self.can_admin:
            return rx.toast.error("Access denied: admin only.")

        with get_session() as session:
            session.info["actor"] = self.audit_actor(source="admin-roles")
            try:
                role = grant_role(session, user_id=user_id, app=app, role="moderator")
                user = session.get(Users, user_id)
            except Exception:
                return rx.toast.error("Erreur lors de l'ajout du rôle.")

        if not user:
            return rx.toast.error("Utilisateur introuvable.")

        exists = any(
            entry["app"] == app
            and entry["role"] == "moderator"
            and entry["user_id"] == user_id
            for entry in self.roles
        )
        if not exists:
            self.roles = [
                *self.roles,
                {
                    "id": role.id,
                    "app": app,
                    "role": "moderator",
                    "user_id": user_id,
                    "user_email": user.email or "",
                },
            ]
        return rx.toast.success("Rôle modérateur accordé.")

    def revoke_app_moderator(self, app: str, user_id: int):
        if not self.can_admin:
            return rx.toast.error("Access denied: admin only.")

        with get_session() as session:
            session.info["actor"] = self.audit_actor(source="admin-roles")
            removed = revoke_role(session, user_id=user_id, app=app, role="moderator")
            if not removed:
                return rx.toast.error("Rôle introuvable.")

        self.roles = [
            entry
            for entry in self.roles
            if not (
                entry["app"] == app
                and entry["role"] == "moderator"
                and entry["user_id"] == user_id
            )
        ]
        return rx.toast.success("Rôle modérateur retiré.")

    @rx.var
    def filtered_users(self) -> list[dict]:
        return self._compute_filtered_users()

    @rx.var
    def current_users(self) -> list[dict]:
        users = self._compute_filtered_users()
        sort_key = self.sort_value or "email"

        def _key(item: dict):
            value = item.get(sort_key)
            if isinstance(value, str):
                return value.lower()
            if value is None:
                return ""
            return value

        return sorted(users, key=_key)

    def _compute_filtered_users(self) -> list[dict]:
        query = (self.search_query or "").strip().lower()
        if not query:
            return self.users
        return [
            user
            for user in self.users
            if query in (user.get("email") or "").lower()
            or query in (user.get("given_name") or "").lower()
            or query in (user.get("family_name") or "").lower()
            or query in (user.get("immutable_id") or "").lower()
            or query in str(user.get("source_domain", "")).lower()
        ]

    @rx.event(background=True)
    async def load_vendors(self):
        async with self:
            self.is_loading_vendors = True

        with get_session() as session:
            vendors = list_vendors(session, include_inactive=True)

        async with self:
            self.vendors = [
                {
                    "id": vendor.id,
                    "code": vendor.code,
                    "description": vendor.description or "",
                    "portfolio": vendor.portfolio or "",
                    "is_active": bool(vendor.is_active),
                }
                for vendor in vendors
            ]
            self.is_loading_vendors = False

    @rx.var
    def portfolios(self) -> list[str]:
        portfolios = {vendor["portfolio"] for vendor in self.vendors if vendor["portfolio"]}
        return sorted(portfolios)

    @rx.var
    def filtered_vendors(self) -> list[dict]:
        vendors = self.vendors
        if self.vendor_search:
            search = self.vendor_search.lower()
            vendors = [v for v in vendors if search in v["code"].lower()]
        if self.portfolio_filter:
            vendors = [v for v in vendors if v["portfolio"] == self.portfolio_filter]
        if not self.include_inactive:
            vendors = [v for v in vendors if v["is_active"]]
        return vendors

    def create_vendor(self):
        code = (self.new_vendor_code or "").strip()
        if not code:
            return rx.toast.error("Code vendor requis.")

        with get_session() as session:
            session.info["actor"] = self.audit_actor(source="admin-vendors")
            try:
                create_vendor(
                    session,
                    code=code,
                    description=(self.new_vendor_description or "").strip() or None,
                    portfolio=(self.new_vendor_portfolio or "").strip() or None,
                    is_active=True,
                )
            except Exception:
                return rx.toast.error("Erreur lors de la création du vendor.")

        self.new_vendor_code = ""
        self.new_vendor_description = ""
        self.new_vendor_portfolio = ""
        return [
            rx.toast.success("Vendor ajouté."),
            AdminState.load_vendors,
        ]

    def toggle_vendor_active(self, vendor_id: int, is_active: bool):
        with get_session() as session:
            session.info["actor"] = self.audit_actor(source="admin-vendors")
            updated = toggle_vendor_active(session, vendor_id, is_active)
        if not updated:
            return rx.toast.error("Vendor introuvable.")

        self.vendors = [
            {**vendor, "is_active": bool(is_active)} if vendor["id"] == vendor_id else vendor
            for vendor in self.vendors
        ]
        return rx.toast.success("Vendor mis à jour.")

    def _update_user(self, user_id: int, **updates: bool):
        current = next((user for user in self.users if user["id"] == user_id), None)
        if not current:
            return rx.toast.error("Utilisateur introuvable.")

        next_values = {
            "is_active": bool(current.get("is_active", False)),
            "is_validated": bool(current.get("is_validated", False)),
            "is_admin": bool(current.get("is_admin", False)),
        }
        next_values.update({k: bool(v) for k, v in updates.items()})

        with get_session() as session:
            session.info["actor"] = self.audit_actor(source="admin-users")
            updated = update_user_flags(
                session=session,
                user_id=user_id,
                is_active=next_values["is_active"],
                is_validated=next_values["is_validated"],
                is_admin=next_values["is_admin"],
            )

        if not updated:
            return rx.toast.error("Erreur: mise à jour impossible.")

        self.users = [
            {**user, **next_values} if user["id"] == user_id else user
            for user in self.users
        ]
        return rx.toast.success("Droits mis à jour.")

    def toggle_active(self, user_id: int, value: bool):
        return self._update_user(user_id, is_active=value)

    def toggle_validated(self, user_id: int, value: bool):
        return self._update_user(user_id, is_validated=value)

    def toggle_admin(self, user_id: int, value: bool):
        return self._update_user(user_id, is_admin=value)
