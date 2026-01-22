import reflex as rx
from sqlmodel import select

from haleonv3.db.database import get_session
from haleonv3.db.crud.users import update_user_flags
from haleonv3.db.model.users import Users


class AdminState(rx.State):
    is_loading: bool = False
    users: list[dict] = []
    search_query: str = ""
    columns: list[dict] = [
        {"title": "ID", "id": "id", "type": "int", "editable": False},
        {"title": "Immutable ID", "id": "immutable_id", "type": "str", "editable": False},
        {"title": "Email", "id": "email", "type": "str", "editable": False},
        {"title": "Prénom", "id": "given_name", "type": "str", "editable": False},
        {"title": "Nom", "id": "family_name", "type": "str", "editable": False},
        {"title": "Active", "id": "is_active", "type": "bool", "editable": True},
        {"title": "Validated", "id": "is_validated", "type": "bool", "editable": True},
        {"title": "Admin", "id": "is_admin", "type": "bool", "editable": True},
    ]

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

    @rx.var
    def filtered_users(self) -> list[dict]:
        return self._compute_filtered_users()

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

    def on_cell_edited(self, cell: tuple[int, int], grid_cell: dict):
        col_index, row_index = cell
        if row_index < 0 or col_index < 0:
            return
        if col_index >= len(self.columns):
            return

        column_id = self.columns[col_index]["id"]
        if column_id not in {"is_active", "is_validated", "is_admin"}:
            return

        filtered_users = self._compute_filtered_users()
        if row_index >= len(filtered_users):
            return

        user_row = filtered_users[row_index]
        user_id = user_row.get("id")
        if not user_id:
            return rx.toast.error("Utilisateur introuvable.")

        new_value = grid_cell.get("data")
        if not isinstance(new_value, bool):
            return rx.toast.error("Valeur invalide.")

        updated_values = {
            "is_active": user_row.get("is_active", False),
            "is_validated": user_row.get("is_validated", False),
            "is_admin": user_row.get("is_admin", False),
        }
        updated_values[column_id] = new_value

        with next(get_session()) as session:
            updated = update_user_flags(
                session=session,
                user_id=user_id,
                is_active=updated_values["is_active"],
                is_validated=updated_values["is_validated"],
                is_admin=updated_values["is_admin"],
            )

        if not updated:
            return rx.toast.error("Erreur: mise à jour impossible.")

        updated_list = []
        for user in self.users:
            if user["id"] == user_id:
                user = {**user, column_id: new_value}
            updated_list.append(user)
        self.users = updated_list

        return rx.toast.success("Droits mis à jour.")
