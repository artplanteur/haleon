"""Opérations CRUD pour la table UserApplicationAccess."""

from sqlmodel import Session, select
from typing import Optional
from haleon.db.model.user_app_access import UserApplicationAccess
from haleon.db.model.users import Users


def get_all_user_app_accesses(session: Session) -> list[UserApplicationAccess]:
    """Récupère tous les accès utilisateur-application."""
    statement = select(UserApplicationAccess)
    return list(session.exec(statement).all())


def get_user_app_access(
    session: Session,
    user_id: int,
    application_id: int,
) -> Optional[UserApplicationAccess]:
    """Récupère un accès spécifique utilisateur-application."""
    statement = select(UserApplicationAccess).where(
        UserApplicationAccess.user_id == user_id,
        UserApplicationAccess.application_id == application_id,
    )
    return session.exec(statement).first()


def grant_user_app_access(
    session: Session,
    user_id: int,
    application_id: int,
    granted_by: Optional[int] = None,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> UserApplicationAccess:
    """Accorde un accès utilisateur-application."""
    # Import local pour éviter les circular imports (permissions -> crud -> audit_logger)
    from haleon.db.audit_logger import AuditLogger
    with AuditLogger.with_context(session, audit_user, audit_source or "admin/access"):
        # Vérifier si l'accès existe déjà
        existing = get_user_app_access(session, user_id, application_id)
        if existing:
            # Mettre à jour granted_by si fourni
            if granted_by:
                existing.granted_by = granted_by
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        # Créer un nouvel accès
        access = UserApplicationAccess(
            user_id=user_id,
            application_id=application_id,
            granted_by=granted_by,
        )
        session.add(access)
        session.commit()
        session.refresh(access)
        return access


def revoke_user_app_access(
    session: Session,
    user_id: int,
    application_id: int,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> bool:
    """Révoque un accès utilisateur-application."""
    from haleon.db.audit_logger import AuditLogger
    with AuditLogger.with_context(session, audit_user, audit_source or "admin/access"):
        access = get_user_app_access(session, user_id, application_id)
        if access:
            session.delete(access)
            session.commit()
            return True
        return False


def get_user_applications(session: Session, user_id: int) -> list[UserApplicationAccess]:
    """Récupère toutes les applications accessibles par un utilisateur."""
    statement = select(UserApplicationAccess).where(
        UserApplicationAccess.user_id == user_id
    )
    return list(session.exec(statement).all())


def get_application_users(session: Session, application_id: int) -> list[UserApplicationAccess]:
    """Récupère tous les utilisateurs ayant accès à une application."""
    statement = select(UserApplicationAccess).where(
        UserApplicationAccess.application_id == application_id
    )
    return list(session.exec(statement).all())










