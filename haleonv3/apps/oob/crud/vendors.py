from datetime import datetime

from sqlmodel import Session, select

from haleonv3.db.model.vendor import Vendor


def create_vendor(
    session: Session,
    code: str,
    description: str | None,
    portfolio: str | None,
    is_active: bool = True,
) -> Vendor:
    vendor = Vendor(
        code=code[:10],
        description=description,
        portfolio=portfolio,
        is_active=is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor


def list_vendors(
    session: Session,
    portfolio: str | None = None,
    code: str | None = None,
    include_inactive: bool = True,
) -> list[Vendor]:
    query = select(Vendor)
    if portfolio:
        query = query.where(Vendor.portfolio == portfolio)
    if code:
        query = query.where(Vendor.code == code)
    if not include_inactive:
        query = query.where(Vendor.is_active.is_(True))
    return list(session.exec(query).all())


def toggle_vendor_active(session: Session, vendor_id: int, is_active: bool) -> Vendor | None:
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        return None
    vendor.is_active = bool(is_active)
    vendor.updated_at = datetime.utcnow()
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor
