"""Opérations CRUD pour la table Logs."""

from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime
from haleon.db.model.logs import Logs


def get_recent_logs(session: Session, limit: int = 100) -> List[Logs]:
    """Récupère les logs les plus récents.
    
    Args:
        session: Session SQLModel
        limit: Nombre maximum de logs à retourner
        
    Returns:
        Liste des logs triés par date décroissante
    """
    statement = select(Logs).order_by(Logs.changed_at.desc()).limit(limit)
    return list(session.exec(statement).all())


def get_logs_by_table(
    session: Session,
    table_name: str,
    limit: Optional[int] = None,
) -> List[Logs]:
    """Récupère les logs pour une table donnée.
    
    Args:
        session: Session SQLModel
        table_name: Nom de la table
        limit: Nombre maximum de logs à retourner (None = pas de limite)
        
    Returns:
        Liste des logs pour la table, triés par date décroissante
    """
    statement = select(Logs).where(Logs.table_name == table_name).order_by(Logs.changed_at.desc())
    if limit:
        statement = statement.limit(limit)
    return list(session.exec(statement).all())


def get_logs_by_user(
    session: Session,
    user_email: str,
    limit: Optional[int] = None,
) -> List[Logs]:
    """Récupère les logs pour un utilisateur donné.
    
    Args:
        session: Session SQLModel
        user_email: Email de l'utilisateur
        limit: Nombre maximum de logs à retourner (None = pas de limite)
        
    Returns:
        Liste des logs pour l'utilisateur, triés par date décroissante
    """
    statement = select(Logs).where(Logs.user_email == user_email).order_by(Logs.changed_at.desc())
    if limit:
        statement = statement.limit(limit)
    return list(session.exec(statement).all())


def get_logs_by_date_range(
    session: Session,
    start_date: datetime,
    end_date: datetime,
    limit: Optional[int] = None,
) -> List[Logs]:
    """Récupère les logs dans une plage de dates.
    
    Args:
        session: Session SQLModel
        start_date: Date de début
        end_date: Date de fin
        limit: Nombre maximum de logs à retourner (None = pas de limite)
        
    Returns:
        Liste des logs dans la plage de dates, triés par date décroissante
    """
    statement = select(Logs).where(
        Logs.changed_at >= start_date,
        Logs.changed_at <= end_date,
    ).order_by(Logs.changed_at.desc())
    if limit:
        statement = statement.limit(limit)
    return list(session.exec(statement).all())


def get_logs_count(session: Session) -> int:
    """Récupère le nombre total de logs.
    
    Args:
        session: Session SQLModel
        
    Returns:
        Nombre total de logs
    """
    statement = select(Logs)
    return len(list(session.exec(statement).all()))


def get_logs_count_by_date_range(
    session: Session,
    start_date: datetime,
    end_date: datetime,
) -> int:
    """Récupère le nombre de logs dans une plage de dates.
    
    Args:
        session: Session SQLModel
        start_date: Date de début
        end_date: Date de fin
        
    Returns:
        Nombre de logs dans la plage de dates
    """
    statement = select(Logs).where(
        Logs.changed_at >= start_date,
        Logs.changed_at <= end_date,
    )
    return len(list(session.exec(statement).all()))


