"""Migration: add auth timestamps to the core `users` table.

Adds:
- last_login_at (DATETIME)
- last_seen_at (DATETIME)
- updated_at (DATETIME)

Also normalizes inconsistent legacy data:
- if session_id is NULL/empty => is_connected must be False
"""

from __future__ import annotations

from pathlib import Path
from sqlmodel import text


def _column_exists(session, table: str, column: str) -> bool:
    """Return True if a column exists in a sqlite table."""
    # NOTE: SQLite's pragma_table_info() is easiest to use with a resulting SQL string.
    # `table` is controlled internally by this module (not user input).
    stmt = text(
        f"""
        SELECT COUNT(*) as count
        FROM pragma_table_info('{table}')
        WHERE name = :column
        """
    ).bindparams(column=column)
    result = session.exec(stmt).first()
    count = result[0] if isinstance(result, tuple) else (getattr(result, "count", 0) or 0)
    return count > 0


def migrate_users_auth_timestamps(session, db_path: Path):
    """Apply migration to the sqlite database if needed (idempotent)."""
    print(f"\n{'='*60}")
    print("Migration: Ajout des colonnes auth timestamps à users")
    print(f"Base de données: {db_path}")
    print(f"{'='*60}\n")

    if not db_path.exists():
        print("[INFO] Base de données non trouvée, migration ignorée (sera créée au démarrage).")
        return

    try:
        table = "users"
        columns_to_add = [
            ("last_login_at", "DATETIME"),
            ("last_seen_at", "DATETIME"),
            ("updated_at", "DATETIME"),
        ]

        for col, col_type in columns_to_add:
            if _column_exists(session, table, col):
                print(f"[OK] Colonne '{col}' existe déjà dans '{table}'")
                continue
            print(f"Ajout de la colonne '{col}'...")
            session.exec(text(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {col_type}'))
            session.commit()
            print(f"[OK] Colonne '{col}' ajoutée")

        # Backfill timestamps from legacy last_connection when available.
        session.exec(
            text(
                """
                UPDATE users
                SET
                    updated_at = COALESCE(updated_at, last_connection, datetime('now')),
                    last_login_at = COALESCE(last_login_at, last_connection),
                    last_seen_at = COALESCE(last_seen_at, last_connection)
                """
            )
        )

        # Normalize connection flags: if no session_id => not connected.
        session.exec(
            text(
                """
                UPDATE users
                SET is_connected = 0
                WHERE session_id IS NULL OR session_id = ''
                """
            )
        )
        session.commit()
        print("[OK] Backfill et normalisation appliqués")
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la migration users auth timestamps: {e}")
        import traceback

        traceback.print_exc()
        session.rollback()
        raise


if __name__ == "__main__":
    # Standalone execution convenience.
    from sqlmodel import Session
    from haleon.db.database import DB_PATH, engine

    with Session(engine) as s:
        migrate_users_auth_timestamps(s, DB_PATH)


