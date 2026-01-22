import reflex as rx
from sqlmodel import select

from haleonv3.db.database import get_session
from haleonv3.db.crud.users import update_user_flags
from haleonv3.db.model.users import Users


class AdminState(rx.State):
    is_loading: bool = False
    users: list[dict] = []
    search_query: str = ""
    sort_value: str = "email"

    @rx.event(background=True)
    async def load_users(self):
        async with self:
            self.is_loading = True

        with next(get_session()) as session:
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
                }
                for u in rows
            ]
            self.is_loading = False

    def set_search_query(self, value: str):
        self.search_query = value or ""

    def set_sort_value(self, value: str):
        self.sort_value = value or "email"

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
        ]

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

        with next(get_session()) as session:
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
