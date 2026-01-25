import reflex as rx
from sqlmodel import select

from haleonv3.apps.oob.crud.access import grant_vendor_access, revoke_vendor_access
from haleonv3.apps.oob.crud.vendors import create_vendor, list_vendors, toggle_vendor_active
from haleonv3.db.database import get_session
from haleonv3.db.model.users import Users
from haleonv3.db.model.vendor import Vendor
from haleonv3.db.model.vendor_access import UserVendorAccess


class OOBAdminState(rx.State):
    is_loading_vendors: bool = False
    is_loading_access: bool = False
    is_loading_users: bool = False

    vendors: list[dict] = []
    vendor_access: list[dict] = []
    users: list[dict] = []

    vendor_search: str = ""
    portfolio_filter: str = ""
    include_inactive: bool = True

    new_vendor_code: str = ""
    new_vendor_description: str = ""
    new_vendor_portfolio: str = ""

    selected_user_id: int | None = None
    selected_access_level: str = "read"
    selected_vendor_ids: list[int] = []
    selected_portfolio: str = ""

    @rx.event(background=True)
    async def load_vendors(self):
        async with self:
            self.is_loading_vendors = True

        with next(get_session()) as session:
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

    @rx.event(background=True)
    async def load_users(self):
        async with self:
            self.is_loading_users = True

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
            self.is_loading_users = False

    @rx.event(background=True)
    async def load_access(self):
        async with self:
            self.is_loading_access = True

        with next(get_session()) as session:
            rows = session.exec(
                select(UserVendorAccess, Vendor, Users)
                .join(Vendor, Vendor.id == UserVendorAccess.vendor_id)
                .join(Users, Users.id == UserVendorAccess.user_id)
            ).all()

        async with self:
            self.vendor_access = [
                {
                    "id": access.id,
                    "user_id": access.user_id,
                    "user_email": user.email or "",
                    "vendor_id": access.vendor_id,
                    "vendor_code": vendor.code,
                    "portfolio": vendor.portfolio or "",
                    "access_level": access.access_level,
                }
                for access, vendor, user in rows
            ]
            self.is_loading_access = False

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

    def set_selected_user(self, value: str):
        try:
            self.selected_user_id = int(value)
        except (TypeError, ValueError):
            self.selected_user_id = None

    def set_selected_access_level(self, value: str):
        self.selected_access_level = value or "read"

    def set_selected_portfolio(self, value: str):
        self.selected_portfolio = value or ""

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

    @rx.var
    def portfolio_vendors(self) -> list[dict]:
        if not self.selected_portfolio:
            return self.vendors
        return [v for v in self.vendors if v["portfolio"] == self.selected_portfolio]

    @rx.var
    def is_portfolio_all_selected(self) -> bool:
        if not self.portfolio_vendors:
            return False
        portfolio_ids = {vendor["id"] for vendor in self.portfolio_vendors}
        return portfolio_ids.issubset(set(self.selected_vendor_ids))

    def create_vendor(self):
        code = (self.new_vendor_code or "").strip()
        if not code:
            return rx.toast.error("Code vendor requis.")

        with next(get_session()) as session:
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
            OOBAdminState.load_vendors,
        ]

    def toggle_vendor_active(self, vendor_id: int, is_active: bool):
        with next(get_session()) as session:
            updated = toggle_vendor_active(session, vendor_id, is_active)
        if not updated:
            return rx.toast.error("Vendor introuvable.")

        self.vendors = [
            {**vendor, "is_active": bool(is_active)} if vendor["id"] == vendor_id else vendor
            for vendor in self.vendors
        ]
        return rx.toast.success("Vendor mis à jour.")

    def set_user_vendor_access(self, user_id: int, vendor_id: int, access_level: str):
        with next(get_session()) as session:
            try:
                access = grant_vendor_access(session, user_id, vendor_id, access_level)
                vendor = session.get(Vendor, vendor_id)
                user = session.get(Users, user_id)
            except Exception:
                return rx.toast.error("Erreur lors de la mise à jour de l'accès.")

        if not vendor or not user:
            return rx.toast.error("Données introuvables.")

        updated = False
        updated_list = []
        for entry in self.vendor_access:
            if entry["user_id"] == user_id and entry["vendor_id"] == vendor_id:
                updated_list.append(
                    {
                        **entry,
                        "access_level": access_level,
                    }
                )
                updated = True
            else:
                updated_list.append(entry)
        if not updated:
            updated_list.append(
                {
                    "id": access.id,
                    "user_id": user_id,
                    "user_email": user.email or "",
                    "vendor_id": vendor_id,
                    "vendor_code": vendor.code,
                    "portfolio": vendor.portfolio or "",
                    "access_level": access_level,
                }
            )
        self.vendor_access = updated_list
        return rx.toast.success("Accès mis à jour.")

    def remove_user_vendor_access(self, user_id: int, vendor_id: int):
        with next(get_session()) as session:
            removed = revoke_vendor_access(session, user_id, vendor_id)
        if not removed:
            return rx.toast.error("Accès introuvable.")

        self.vendor_access = [
            entry
            for entry in self.vendor_access
            if not (entry["user_id"] == user_id and entry["vendor_id"] == vendor_id)
        ]
        return rx.toast.success("Accès supprimé.")

    def toggle_vendor_selection(self, vendor_id: int, checked: bool):
        vendor_id = int(vendor_id)
        selected = set(self.selected_vendor_ids)
        if checked:
            selected.add(vendor_id)
        else:
            selected.discard(vendor_id)
        self.selected_vendor_ids = list(selected)

    def select_all_portfolio(self, checked: bool):
        if checked:
            self.selected_vendor_ids = [v["id"] for v in self.portfolio_vendors]
        else:
            self.selected_vendor_ids = []

    def apply_access_to_selected(self):
        if not self.selected_user_id:
            return rx.toast.error("Sélectionne un utilisateur.")
        if not self.selected_vendor_ids:
            return rx.toast.error("Sélectionne au moins un vendor.")

        with next(get_session()) as session:
            for vendor_id in self.selected_vendor_ids:
                grant_vendor_access(
                    session,
                    self.selected_user_id,
                    int(vendor_id),
                    self.selected_access_level,
                )

        return [
            rx.toast.success("Accès appliqué."),
            OOBAdminState.load_access,
        ]

    def remove_access_from_selected(self):
        if not self.selected_user_id:
            return rx.toast.error("Sélectionne un utilisateur.")
        if not self.selected_vendor_ids:
            return rx.toast.error("Sélectionne au moins un vendor.")

        with next(get_session()) as session:
            for vendor_id in self.selected_vendor_ids:
                revoke_vendor_access(session, self.selected_user_id, int(vendor_id))

        return [
            rx.toast.success("Accès supprimés."),
            OOBAdminState.load_access,
        ]
