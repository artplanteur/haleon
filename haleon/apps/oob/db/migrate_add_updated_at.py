"""Migration pour ajouter la colonne updated_at à la table app_OOB_Comment."""

from haleon.db.database import get_session, DB_PATH, engine
from sqlmodel import text
from pathlib import Path


def migrate_add_updated_at():
    """Ajoute la colonne updated_at à la table app_OOB_Comment si elle n'existe pas."""
    print(f"\n{'='*60}")
    print("Migration: Ajout de la colonne updated_at à app_OOB_Comment")
    print(f"Base de données: {DB_PATH}")
    print(f"{'='*60}\n")
    
    if not DB_PATH.exists():
        print("[ERREUR] Base de donnees non trouvee!")
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
            print("[OK] La colonne 'updated_at' existe deja dans la table app_OOB_Comment")
            return
        
        # Ajouter la colonne updated_at
        print("Ajout de la colonne 'updated_at'...")
        session.exec(
            text("""
                ALTER TABLE app_OOB_Comment 
                ADD COLUMN updated_at DATETIME
            """)
        )
        session.commit()
        
        print("[OK] Colonne 'updated_at' ajoutee avec succes a la table app_OOB_Comment")
        
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate_add_updated_at()



