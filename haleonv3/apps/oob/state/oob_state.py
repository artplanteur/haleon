import asyncio
import pandas as pd
import reflex as rx
from sqlmodel import select

from haleonv3.db.database import get_session
from haleonv3.db.model.users import Users
from haleonv3.db.model.vendor import Vendor
from haleonv3.apps.oob.model.user_vendor_access import UserVendorAccess
from haleonv3.state.auth_state import AuthState

class OOBState(AuthState):
    is_loading: bool = False
    progress: int = 0
    rows: list[dict] = []

    # Vendors the current user can access in OOB (used later to load PO/vendor data).
    is_loading_vendors: bool = False
    allowed_vendor_ids: list[int] = []
    allowed_vendors: list[dict] = []

    @rx.event(background=True)
    async def load_allowed_vendors(self):
        """Load allowed vendors for the current user.

        Rules (simple):
        - if global admin OR OOB moderator => access to all vendors (write)
        - else => all vendors are at least (read), and vendors present in user_vendor_access
          with access_level="write" are upgraded to (write)
        """
        async with self:
            self.is_loading_vendors = True
            self.allowed_vendor_ids = []
            self.allowed_vendors = []

        immutable_id = (self.immutable_id or "").strip()
        if not immutable_id:
            async with self:
                self.is_loading_vendors = False
            return

        with get_session() as session:
            user = session.exec(select(Users).where(Users.immutable_id == immutable_id)).first()
            if not user:
                async with self:
                    self.is_loading_vendors = False
                return

            # Moderator: all vendors (implicit write).
            if bool(self.can_moderate_oob):
                vendors = list(session.exec(select(Vendor)).all())
                allowed = [
                    {
                        "vendor_id": v.id,
                        "vendor_code": v.code,
                        "portfolio": v.portfolio or "",
                        "access_level": "write",
                    }
                    for v in vendors
                ]
            else:
                vendors = list(session.exec(select(Vendor)).all())
                # Default: everyone can read all vendors.
                vendor_map = {
                    int(v.id): {
                        "vendor_id": v.id,
                        "vendor_code": v.code,
                        "portfolio": v.portfolio or "",
                        "access_level": "read",
                    }
                    for v in vendors
                }

                # Upgrade to write where configured.
                access_rows = session.exec(
                    select(UserVendorAccess).where(UserVendorAccess.user_id == user.id)
                ).all()
                for access in access_rows:
                    if access.access_level == "write" and access.vendor_id in vendor_map:
                        vendor_map[int(access.vendor_id)]["access_level"] = "write"

                allowed = list(vendor_map.values())

        async with self:
            self.allowed_vendors = allowed
            self.allowed_vendor_ids = [int(row["vendor_id"]) for row in allowed if row.get("vendor_id") is not None]
            self.is_loading_vendors = False

    @rx.event(background=True)
    async def load_oob(self):
        """One button: load vendors, then load data."""
        await self.load_allowed_vendors()
        await self.load_oob_data()

    @staticmethod
    def _fake_api_dataframe(total_rows: int = 800) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "po": [f"PO-{idx:05d}" for idx in range(1, total_rows + 1)],
                "vendor": [f"V{(idx % 7) + 1:03d}" for idx in range(1, total_rows + 1)],
                "amount": [500 + (idx * 37) % 5000 for idx in range(1, total_rows + 1)],
                "status": ["Open" if idx % 3 else "Closed" for idx in range(1, total_rows + 1)],
            }
        )

    @rx.event(background=True)
    async def load_oob_data(self):
        total_steps = 30
        async with self:
            self.is_loading = True
            self.progress = 0
            self.rows = []

        for step in range(1, total_steps + 1):
            await asyncio.sleep(0.2)
            async with self:
                self.progress = int(step / total_steps * 100)

        df = self._fake_api_dataframe()
        async with self:
            self.rows = df.to_dict("records")
            self.is_loading = False
