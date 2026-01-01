"""Opérations CRUD pour la table Users."""

from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
from haleon.db.model.users import Users
from haleon.db.audit_logger import AuditLogger


def get_user_by_email(session: Session, email: str) -> Optional[Users]:
    """Récupère un utilisateur par son email."""
    statement = select(Users).where(Users.email == email)
    return session.exec(statement).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[Users]:
    """Récupère un utilisateur par son ID."""
    return session.get(Users, user_id)


def get_user_by_session_id(session: Session, session_id: str) -> Optional[Users]:
    """Récupère un utilisateur par son session_id."""
    statement = select(Users).where(Users.session_id == session_id)
    return session.exec(statement).first()


def get_all_users(session: Session) -> list[Users]:
    """Récupère tous les utilisateurs."""
    statement = select(Users)
    return list(session.exec(statement).all())


def create_user(
    session: Session,
    email: str,
    family_name: Optional[str] = None,
    first_name: Optional[str] = None,
    country: Optional[str] = None,
    session_id: Optional[str] = None,
    is_connected: bool = False,
    is_admin: bool = False,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Users:
    """Crée un nouvel utilisateur.
    
    Args:
        session: Session SQLModel
        email: Email de l'utilisateur
        family_name: Nom de famille
        first_name: Prénom
        country: Pays
        session_id: ID de session
        is_connected: Statut de connexion initial (par défaut: False)
        is_admin: Si l'utilisateur est admin
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "admin/users", "seed")
    """
    now = datetime.now()
    with AuditLogger.with_context(session, audit_user, audit_source):
        user = Users(
            email=email,
            family_name=family_name,
            first_name=first_name,
            country=country,
            session_id=session_id,
            is_connected=is_connected,
            is_validated=False,  # Par défaut, nouvel utilisateur non validé
            is_active=True,
            is_admin=is_admin,
            # Legacy: retained for older code/DBs, but auth now uses last_login_at/last_seen_at.
            last_connection=now if is_connected else None,
            last_login_at=now if is_connected else None,
            last_seen_at=now if is_connected else None,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def update_user(
    session: Session,
    user: Users,
    family_name: Optional[str] = None,
    first_name: Optional[str] = None,
    country: Optional[str] = None,
    session_id: Optional[str] = None,
    is_connected: Optional[bool] = None,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Users:
    """Met à jour un utilisateur existant.
    
    Args:
        session: Session SQLModel
        user: Utilisateur à mettre à jour
        family_name: Nouveau nom de famille
        first_name: Nouveau prénom
        country: Nouveau pays
        session_id: Nouvel ID de session
        is_connected: Nouveau statut de connexion
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "admin/users")
    """
    now = datetime.now()
    with AuditLogger.with_context(session, audit_user, audit_source):
        if family_name is not None:
            user.family_name = family_name
        if first_name is not None:
            user.first_name = first_name
        if country is not None:
            user.country = country
        if session_id is not None:
            user.session_id = session_id
        if is_connected is not None:
            user.is_connected = is_connected
        user.updated_at = now
        
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def login_user(
    session: Session,
    user: Users,
    session_id: str,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Users:
    """Mark a user as logged in and issue a new session id.

    This sets:
    - is_connected = True
    - session_id = provided session_id
    - last_login_at = now
    - last_seen_at = now
    - updated_at = now
    """
    now = datetime.now()
    with AuditLogger.with_context(session, audit_user, audit_source):
        user.session_id = session_id
        user.is_connected = True
        user.last_login_at = now
        user.last_seen_at = now
        user.updated_at = now
        # Legacy (kept for compatibility / migration backfill)
        user.last_connection = now
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def touch_user_last_seen(
    session: Session,
    user: Users,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Users:
    """Update user last_seen_at (activity heartbeat)."""
    now = datetime.now()
    with AuditLogger.with_context(session, audit_user, audit_source):
        user.last_seen_at = now
        user.updated_at = now
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def logout_user(
    session: Session,
    user: Users,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Users:
    """Log out a user (server-side): clear session_id and is_connected."""
    now = datetime.now()
    with AuditLogger.with_context(session, audit_user, audit_source):
        user.is_connected = False
        user.session_id = None
        user.updated_at = now
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def toggle_user_active(
    session: Session,
    user: Users,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Users:
    """Active/désactive un utilisateur.
    
    Args:
        session: Session SQLModel
        user: Utilisateur à modifier
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "admin/users")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        user.is_active = not user.is_active
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def toggle_user_validated(
    session: Session,
    user: Users,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Users:
    """Valide/invalide un utilisateur.
    
    Args:
        session: Session SQLModel
        user: Utilisateur à modifier
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "admin/users")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        user.is_validated = not user.is_validated
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def toggle_user_admin(
    session: Session,
    user: Users,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Users:
    """Donne/retire les droits admin à un utilisateur.
    
    Args:
        session: Session SQLModel
        user: Utilisateur à modifier
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "admin/users")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        user.is_admin = not user.is_admin
        session.add(user)
        session.commit()
        session.refresh(user)
    return user










