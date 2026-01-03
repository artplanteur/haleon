"""Migration pour ajouter la colonne updated_at à la table app_OOB_Comment."""

import logging
from haleon.db.database import get_session, DB_PATH, engine
from sqlmodel import text
from pathlib import Path

logger = logging.getLogger("haleon.apps.oob.migrations")

def migrate_add_updated_at():
    """Ajoute la colonne updated_at à la table app_OOB_Comment si elle n'existe pas."""
    logger.info("Migration add updated_at to app_OOB_Comment (db=%s)", DB_PATH)
    
    if not DB_PATH.exists():
        logger.warning("DB not found, skipping migration.")
        return
    
    session_gen = get_session()
    session = next(session_gen)
    try:
        # Vérifier si la colonne existe déjà
        result = session.exec(
            text("""
                SELECT COUNT(*) as count 
                FROM pragma_table_info('app_OOB_Comment') 
                WHERE name = 'updated_at'
            """)
        ).first()
        
        # result est un tuple (count,), extraire la valeur
        count = result[0] if isinstance(result, tuple) else (result.count if hasattr(result, 'count') else 0)
        
        if count > 0:
            logger.debug("Column updated_at already exists in app_OOB_Comment")
            return
        
        # Ajouter la colonne updated_at
        logger.info("Adding column updated_at...")
        session.exec(
            text("""
                ALTER TABLE app_OOB_Comment 
                ADD COLUMN updated_at DATETIME
            """)
        )
        session.commit()
        
        logger.info("Column updated_at added to app_OOB_Comment")
        
    except Exception as e:
        logger.exception("Migration add updated_at failed: %s", e)
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate_add_updated_at()



