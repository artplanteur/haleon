from datetime import datetime

from sqlmodel import Session, select

from haleonv3.db.model.user_role import UserRole


def grant_role(session: Session, user_id: int, app: str, role: str) -> UserRole:
    existing = session.exec(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.app == app,
            UserRole.role == role,
        )
    ).first()
    if existing:
        return existing
    role_entry = UserRole(
        user_id=user_id,
        app=app,
        role=role,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(role_entry)
    session.commit()
    session.refresh(role_entry)
    return role_entry


def revoke_role(session: Session, user_id: int, app: str, role: str) -> bool:
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


def list_roles_for_app(session: Session, app: str) -> list[UserRole]:
    return list(session.exec(select(UserRole).where(UserRole.app == app)))


def list_roles_for_user(session: Session, user_id: int) -> list[UserRole]:
    return list(session.exec(select(UserRole).where(UserRole.user_id == user_id)))
