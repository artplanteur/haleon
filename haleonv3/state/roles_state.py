from pathlib import Path

import reflex as rx
from sqlmodel import select

from haleonv3.apps.oob.crud.roles import grant_role
from haleonv3.db.database import get_session
from haleonv3.db.model.users import Users
from haleonv3.db.model.user_role import UserRole


class RolesState(rx.State):
    is_loading: bool = False
    apps: list[str] = []
    users: list[dict] = []
    roles: list[dict] = []
    user_search: str = ""

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

    def grant_app_admin(self, app: str, user_id: int):
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

    def revoke_app_admin(self, app: str, user_id: int):
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
