from pathlib import Path

import json
import time

import reflex as rx
from sqlmodel import select

from haleonv3.apps.oob.crud.roles import grant_role
from haleonv3.db.database import get_session
from haleonv3.db.model.users import Users
from haleonv3.db.model.user_role import UserRole
from haleonv3.state.auth_state import AuthState


class RolesState(AuthState):
    is_loading: bool = False
    apps: list[str] = []
    users: list[dict] = []
    roles: list[dict] = []
    user_search: str = ""
    selected_user_id: int | None = None
    selected_app: str = ""

    @rx.event(background=True)
    async def load_apps(self):
        async with self:
            self.is_loading = True

        apps_dir = Path(__file__).resolve().parents[1] / "apps"
        apps = []
        if apps_dir.exists():
            for entry in apps_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("__"):
                    apps.append(entry.name.lower())

        async with self:
            self.apps = sorted(apps)
            self.is_loading = False

    @rx.event(background=True)
    async def load_users(self):
        async with self:
            self.is_loading = True

        with next(get_session()) as session:
            users = session.exec(select(Users)).all()

        async with self:
            self.users = [
                {
                    "id": user.id,
                    "email": user.email or "",
                    "given_name": user.given_name or "",
                    "family_name": user.family_name or "",
                }
                for user in users
            ]
            self.is_loading = False

    @rx.event(background=True)
    async def load_roles(self):
        async with self:
            self.is_loading = True

        with next(get_session()) as session:
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
            self.is_loading = False

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
    def filtered_users(self) -> list[dict]:
        query = (self.user_search or "").strip().lower()
        if not query:
            return self.users
        return [
            user
            for user in self.users
            if query in (user.get("email") or "").lower()
            or query in (user.get("given_name") or "").lower()
            or query in (user.get("family_name") or "").lower()
        ]

    @rx.var
    def user_options(self) -> list[dict]:
        return [{"label": user["email"], "value": user["id"]} for user in self.users]

    def grant_selected_admin(self):
        if not self.selected_user_id:
            return rx.toast.error("Sélectionne un utilisateur.")
        if not self.selected_app:
            return rx.toast.error("Sélectionne une application.")
        return self.grant_app_admin(self.selected_app, self.selected_user_id)

    def grant_app_admin(self, app: str, user_id: int):
        # #region agent log
        try:
            with open(r"c:\python\haleonv3\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "H4",
                            "location": "state/roles_state.py:grant_app_admin",
                            "message": "grant_app_admin",
                            "data": {"app": app, "user_id": user_id},
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        with next(get_session()) as session:
            try:
                role = grant_role(session, user_id, app, "admin")
                user = session.get(Users, user_id)
            except Exception:
                return rx.toast.error("Erreur lors de l'ajout du rôle.")

        if not user:
            return rx.toast.error("Utilisateur introuvable.")

        exists = any(
            entry["app"] == app
            and entry["role"] == "admin"
            and entry["user_id"] == user_id
            for entry in self.roles
        )
        if not exists:
            self.roles = [
                *self.roles,
                {
                    "id": role.id,
                    "app": app,
                    "role": "admin",
                    "user_id": user_id,
                    "user_email": user.email or "",
                },
            ]
        return rx.toast.success("Rôle admin accordé.")

    @rx.var
    def is_global_admin(self) -> bool:
        return self.can_admin

    def is_app_admin(self, app: str) -> bool:
        if self.is_global_admin:
            return True
        return any(
            entry["app"] == app and entry["role"] == "admin" for entry in self.roles
        )

    def revoke_app_admin(self, app: str, user_id: int):
        # #region agent log
        try:
            with open(r"c:\python\haleonv3\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "H5",
                            "location": "state/roles_state.py:revoke_app_admin",
                            "message": "revoke_app_admin",
                            "data": {"app": app, "user_id": user_id},
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        with next(get_session()) as session:
            role = session.exec(
                select(UserRole).where(
                    UserRole.user_id == user_id,
                    UserRole.app == app,
                    UserRole.role == "admin",
                )
            ).first()
            if not role:
                return rx.toast.error("Rôle introuvable.")
            session.delete(role)
            session.commit()

        self.roles = [
            entry
            for entry in self.roles
            if not (
                entry["app"] == app
                and entry["role"] == "admin"
                and entry["user_id"] == user_id
            )
        ]
        return rx.toast.success("Rôle admin retiré.")
