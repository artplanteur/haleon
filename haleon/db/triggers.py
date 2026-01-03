"""Génération dynamique de triggers SQLite pour l'audit de toutes les tables."""

import json
import logging
from sqlmodel import Session
from sqlalchemy import inspect, text
from typing import List, Set

logger = logging.getLogger("haleon.db.triggers")

# Tables à exclure de l'audit (pour éviter la récursion)
EXCLUDED_TABLES: Set[str] = {
    "logs",  # La table Logs elle-même
    "sqlite_sequence",  # Table système SQLite
    "_audit_context",  # Table temporaire de contexte
}


def get_table_columns(session: Session, table_name: str) -> List[str]:
    """Récupère la liste des colonnes d'une table.
    
    Args:
        session: Session SQLModel
        table_name: Nom de la table
        
    Returns:
        Liste des noms de colonnes
    """
    inspector = inspect(session.bind)
    columns = inspector.get_columns(table_name)
    return [col["name"] for col in columns]


def create_audit_triggers(session: Session, table_name: str):
    """Crée les triggers d'audit pour une table donnée.
    
    Crée trois triggers :
    - INSERT : Log chaque champ avec old_value=NULL, new_value=valeur
    - UPDATE : Log chaque champ modifié (comparer OLD vs NEW)
    - DELETE : Log chaque champ avec old_value=valeur, new_value=NULL
    
    Args:
        session: Session SQLModel
        table_name: Nom de la table à auditer
    """
    if table_name.lower() in EXCLUDED_TABLES:
        return
    
    # Récupérer les colonnes de la table
    columns = get_table_columns(session, table_name)
    
    # Exclure la colonne 'id' pour éviter les logs inutiles
    columns = [col for col in columns if col.lower() != "id"]
    
    if not columns:
        return
    
    # Nom des triggers
    trigger_insert = f"audit_{table_name}_insert"
    trigger_update = f"audit_{table_name}_update"
    trigger_delete = f"audit_{table_name}_delete"
    
    # Supprimer les triggers existants s'ils existent
    drop_audit_triggers(session, table_name)
    
    # ========== TRIGGER INSERT ==========
    # Pour chaque champ, créer une entrée avec old_value=NULL, new_value=valeur
    insert_statements = []
    for col in columns:
        insert_statements.append(f"""
            INSERT INTO logs (
                table_name, record_id, operation, field_name,
                old_value, new_value, changed_at,
                user_email, user_permissions, source, request_id
            )
            SELECT
                '{table_name}',
                NEW.id,
                'INSERT',
                '{col}',
                NULL,
                COALESCE(CAST(NEW.{col} AS TEXT), ''),
                datetime('now'),
                NULL,
                NULL,
                NULL,
                NULL
        """)
    
    # SQLite nécessite que chaque statement soit séparé par un point-virgule
    # On joint les statements avec des points-virgules et des sauts de ligne
    insert_trigger_sql = f"""
        CREATE TRIGGER {trigger_insert}
        AFTER INSERT ON {table_name}
        BEGIN
            {(';' + chr(10)).join(insert_statements)};
        END;
    """
    
    # ========== TRIGGER UPDATE ==========
    # Pour chaque champ modifié, comparer OLD vs NEW et créer une entrée
    update_statements = []
    for col in columns:
        update_statements.append(f"""
            INSERT INTO logs (
                table_name, record_id, operation, field_name,
                old_value, new_value, changed_at,
                user_email, user_permissions, source, request_id
            )
            SELECT
                '{table_name}',
                NEW.id,
                'UPDATE',
                '{col}',
                COALESCE(CAST(OLD.{col} AS TEXT), ''),
                COALESCE(CAST(NEW.{col} AS TEXT), ''),
                datetime('now'),
                NULL,
                NULL,
                NULL,
                NULL
            WHERE (OLD.{col} IS NULL AND NEW.{col} IS NOT NULL) 
               OR (OLD.{col} IS NOT NULL AND NEW.{col} IS NULL)
               OR (OLD.{col} IS NOT NULL AND NEW.{col} IS NOT NULL AND OLD.{col} <> NEW.{col})
        """)
    
    update_trigger_sql = f"""
        CREATE TRIGGER {trigger_update}
        AFTER UPDATE ON {table_name}
        BEGIN
            {(';' + chr(10)).join(update_statements)};
        END;
    """
    
    # ========== TRIGGER DELETE ==========
    # Pour chaque champ, créer une entrée avec old_value=valeur, new_value=NULL
    delete_statements = []
    for col in columns:
        delete_statements.append(f"""
            INSERT INTO logs (
                table_name, record_id, operation, field_name,
                old_value, new_value, changed_at,
                user_email, user_permissions, source, request_id
            )
            SELECT
                '{table_name}',
                OLD.id,
                'DELETE',
                '{col}',
                COALESCE(CAST(OLD.{col} AS TEXT), ''),
                NULL,
                datetime('now'),
                NULL,
                NULL,
                NULL,
                NULL
        """)
    
    delete_trigger_sql = f"""
        CREATE TRIGGER {trigger_delete}
        AFTER DELETE ON {table_name}
        BEGIN
            {(';' + chr(10)).join(delete_statements)};
        END;
    """
    
    # Exécuter les créations de triggers
    try:
        session.execute(text(insert_trigger_sql))
        session.execute(text(update_trigger_sql))
        session.execute(text(delete_trigger_sql))
        session.commit()
        logger.debug("Audit triggers created for table '%s'", table_name)
    except Exception as e:
        logger.exception("Failed to create audit triggers for '%s': %s", table_name, e)
        session.rollback()


def drop_audit_triggers(session: Session, table_name: str):
    """Supprime les triggers d'audit pour une table donnée.
    
    Args:
        session: Session SQLModel
        table_name: Nom de la table
    """
    trigger_names = [
        f"audit_{table_name}_insert",
        f"audit_{table_name}_update",
        f"audit_{table_name}_delete",
    ]
    
    for trigger_name in trigger_names:
        try:
            session.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name}"))
        except Exception as e:
            # Ignorer les erreurs si le trigger n'existe pas
            pass
    
    session.commit()


def create_audit_triggers_for_all_tables(session: Session):
    """Crée les triggers d'audit pour toutes les tables de la base de données.
    
    Args:
        session: Session SQLModel
    """
    inspector = inspect(session.bind)
    all_tables = inspector.get_table_names()
    
    logger.info("Creating audit triggers for %s tables...", len(all_tables))
    
    for table_name in all_tables:
        if table_name.lower() not in EXCLUDED_TABLES:
            create_audit_triggers(session, table_name)
    
    logger.info("Audit triggers created for all tables")


def recreate_audit_triggers(session: Session):
    """Recrée tous les triggers d'audit (utile après une migration).
    
    Args:
        session: Session SQLModel
    """
    inspector = inspect(session.bind)
    all_tables = inspector.get_table_names()
    
    for table_name in all_tables:
        if table_name.lower() not in EXCLUDED_TABLES:
            drop_audit_triggers(session, table_name)
            create_audit_triggers(session, table_name)


def disable_all_audit_triggers(session: Session):
    """Désactive tous les triggers d'audit en les supprimant.
    
    Utile pour des opérations de seed ou de migration où on ne veut pas
    enregistrer les changements dans la table logs.
    
    Args:
        session: Session SQLModel
    """
    inspector = inspect(session.bind)
    all_tables = inspector.get_table_names()
    
    logger.info("Disabling audit triggers for %s tables...", len(all_tables))
    
    for table_name in all_tables:
        if table_name.lower() not in EXCLUDED_TABLES:
            drop_audit_triggers(session, table_name)
    
    logger.info("All audit triggers disabled")


def enable_all_audit_triggers(session: Session):
    """Réactive tous les triggers d'audit en les recréant.
    
    Utile après avoir désactivé les triggers pour les réactiver.
    
    Args:
        session: Session SQLModel
    """
    create_audit_triggers_for_all_tables(session)

