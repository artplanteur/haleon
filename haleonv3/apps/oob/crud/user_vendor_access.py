from datetime import datetime

from sqlmodel import Session, select

from haleonv3.db.model.vendor import Vendor
from haleonv3.apps.oob.model.user_vendor_access import UserVendorAccess


def grant_vendor_access(
    session: Session,
    user_id: int,
    vendor_id: int,
    access_level: str,
) -> UserVendorAccess:
    access = session.exec(
        select(UserVendorAccess).where(
            UserVendorAccess.user_id == user_id,
            UserVendorAccess.vendor_id == vendor_id,
        )
    ).first()
    if access:
        access.access_level = access_level
        access.updated_at = datetime.utcnow()
    else:
        access = UserVendorAccess(
            user_id=user_id,
            vendor_id=vendor_id,
            access_level=access_level,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    session.add(access)
    session.flush()
    session.commit()
    session.refresh(access)
    return access


def revoke_vendor_access(session: Session, user_id: int, vendor_id: int) -> bool:
    access = session.exec(
        select(UserVendorAccess).where(
            UserVendorAccess.user_id == user_id,
            UserVendorAccess.vendor_id == vendor_id,
        )
    ).first()
    if not access:
        return False
    session.delete(access)
    session.flush()
    session.commit()
    return True


def list_access_by_user(session: Session, user_id: int) -> list[UserVendorAccess]:
    return list(
        session.exec(select(UserVendorAccess).where(UserVendorAccess.user_id == user_id))
    )


def list_access_by_vendor(session: Session, vendor_id: int) -> list[UserVendorAccess]:
    return list(
        session.exec(
            select(UserVendorAccess).where(UserVendorAccess.vendor_id == vendor_id)
        )
    )


def bulk_grant_by_portfolio(
    session: Session,
    user_id: int,
    portfolio: str,
    access_level: str,
) -> list[UserVendorAccess]:
    vendors = session.exec(select(Vendor).where(Vendor.portfolio == portfolio)).all()
    updated: list[UserVendorAccess] = []
    for vendor in vendors:
        updated.append(
            grant_vendor_access(session, user_id, vendor.id, access_level)
        )
    return updated
