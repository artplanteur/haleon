"""Opérations CRUD pour la table Applications."""

from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
from haleon.db.model.applications import Applications
from haleon.db.model.users import Users
from haleon.db.audit_logger import AuditLogger


def get_all_applications(session: Session) -> list[Applications]:
    """Récupère toutes les applications."""
    statement = select(Applications)
    return list(session.exec(statement).all())


def get_active_applications(session: Session) -> list[Applications]:
    """Récupère toutes les applications actives."""
    statement = select(Applications).where(Applications.is_active == True)
    return list(session.exec(statement).all())


def get_application_by_code(session: Session, code: str) -> Optional[Applications]:
    """Récupère une application par son code (insensible à la casse).
    
    Le code est normalisé en minuscule pour correspondre aux URLs.
    La recherche est insensible à la casse pour compatibilité.
    """
    from sqlalchemy import func
    # Normaliser le code en minuscule pour la recherche (insensible à la casse)
    code_normalized = code.lower() if code else ""
    # Utiliser func.lower() pour une comparaison insensible à la casse
    statement = select(Applications).where(func.lower(Applications.code) == code_normalized)
    return session.exec(statement).first()


def get_application_by_id(session: Session, app_id: int) -> Optional[Applications]:
    """Récupère une application par son ID."""
    return session.get(Applications, app_id)


def create_application(
    session: Session,
    name: str,
    code: str,
    route: str,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    minimum_requirement: str = "validated",
    is_active: bool = True,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Applications:
    """Crée une nouvelle application.
    
    Le code est normalisé en minuscule pour correspondre aux URLs et aux dossiers.
    Les noms de tables utilisent le code en majuscules : app_{CODE}_* (ex: app_OOB_*).
    
    Args:
        session: Session SQLModel
        name: Nom de l'application
        code: Code de l'application
        route: Route de l'application
        description: Description
        icon: Icône
        minimum_requirement: Exigence minimale
        is_active: Si l'application est active
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "admin/applications", "seed")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        # Normaliser le code en minuscule
        code_normalized = code.lower() if code else ""
        app = Applications(
            name=name,
            code=code_normalized,
            route=route,
            description=description,
            icon=icon,
            minimum_requirement=minimum_requirement,
            is_active=is_active,
            created_at=datetime.now(),
        )
        session.add(app)
        session.commit()
        session.refresh(app)
    return app


def delete_application(
    session: Session,
    app_id: int,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> bool:
    """Supprime une application.
    
    Args:
        session: Session SQLModel
        app_id: ID de l'application à supprimer
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "admin/applications")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        app = session.get(Applications, app_id)
        if app:
            session.delete(app)
            session.commit()
            return True
    return False


def update_application(
    session: Session,
    app: Applications,
    name: Optional[str] = None,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    is_active: Optional[bool] = None,
    route: Optional[str] = None,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Applications:
    """Met à jour une application.
    
    Args:
        session: Session SQLModel
        app: Application à mettre à jour
        name: Nouveau nom
        description: Nouvelle description
        icon: Nouvelle icône
        is_active: Nouveau statut actif
        route: Nouvelle route
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "admin/applications")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        if name is not None:
            app.name = name
        if description is not None:
            app.description = description
        if icon is not None:
            app.icon = icon
        if is_active is not None:
            app.is_active = is_active
        if route is not None:
            app.route = route
        app.updated_at = datetime.now()
        
        session.add(app)
        session.commit()
        session.refresh(app)
    return app
