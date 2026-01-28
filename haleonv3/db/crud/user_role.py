from datetime import datetime

from sqlmodel import Session, select

from haleonv3.db.model.user_role import UserRole


def grant_role(session: Session, user_id: int, app: str, role: str) -> UserRole:
    """Create (or return) a role for a user on an app.

    Example:
        grant_role(session, user_id=12, app="oob", role="moderator")
    """
    existing = session.exec(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.app == app,
            UserRole.role == role,
        )
    ).first()
    if existing:
        return existing

    now = datetime.utcnow()
    entry = UserRole(
        user_id=user_id,
        app=app,
        role=role,
        created_at=now,
        updated_at=now,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def revoke_role(session: Session, user_id: int, app: str, role: str) -> bool:
    """Delete a role. Returns True if deleted, False if not found."""
    existing = session.exec(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.app == app,
            UserRole.role == role,
        )
    ).first()
    if not existing:
        return False
    session.delete(existing)
    session.commit()
    return True


def list_roles_for_user(session: Session, user_id: int) -> list[UserRole]:
    return list(session.exec(select(UserRole).where(UserRole.user_id == user_id)))


def list_roles_for_app(session: Session, app: str) -> list[UserRole]:
    return list(session.exec(select(UserRole).where(UserRole.app == app)))

