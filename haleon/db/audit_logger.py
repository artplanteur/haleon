"""Classe applicative pour gérer le contexte d'audit et journaliser les changements BDD.

Deux mécanismes peuvent coexister :
- contexte via table TEMP `_audit_context` (historique)
- journalisation côté serveur (SQLAlchemy/SQLModel) : dès qu'une opération CRUD fait un flush/commit,
  on écrit dans la table `logs` les changements (INSERT/UPDATE/DELETE) avec le contexte.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlmodel import Session
from sqlalchemy import text, event, inspect as sa_inspect
from sqlalchemy.sql.sqltypes import Boolean
from haleon.db.model.users import Users
from haleon.db.model.logs import Logs


def _to_str(value: Any) -> Optional[str]:
    """Convertit une valeur en string stockable dans Logs."""
    if value is None:
        return None
    # Normalisation bool -> "true"/"false" (cohérent avec JSON)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _normalize_by_column_type(value: Any, column_type: Any) -> Any:
    """Normalise une valeur selon le type SQLAlchemy de la colonne (ex: bool)."""
    if value is None:
        return None
    try:
        is_bool = isinstance(column_type, Boolean)
    except Exception:
        is_bool = False
    if is_bool:
        # SQLite peut renvoyer 0/1 pour des booleans.
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str) and value.lower() in ("0", "1", "true", "false"):
            return value.lower() in ("1", "true")
        if isinstance(value, bool):
            return value
    return value


def _get_table_name(obj: Any) -> str:
    try:
        return sa_inspect(obj).mapper.local_table.name
    except Exception:
        return getattr(obj, "__tablename__", obj.__class__.__name__)


def _get_record_id(obj: Any) -> Optional[int]:
    # Convention principale du projet: colonne id
    rid = getattr(obj, "id", None)
    if isinstance(rid, int):
        return rid
    try:
        ident = sa_inspect(obj).identity
        if ident and isinstance(ident[0], int):
            return ident[0]
    except Exception:
        pass
    return None


def _audit_before_flush(session: Session, flush_context, instances):
    """Capture les changements avant flush (updates/deletes) et prépare les inserts."""
    if session.info.get("_audit_logging_disabled"):
        return

    # Préparer la liste des inserts à logger après que les IDs soient assignés.
    pending: List[Tuple[Any, str, Dict[str, Any]]] = session.info.setdefault("_audit_pending_inserts", [])

    # Inserts
    for obj in list(session.new):
        if isinstance(obj, Logs):
            continue
        table_name = _get_table_name(obj)
        insp = sa_inspect(obj)
        values: Dict[str, Any] = {}
        for attr in insp.mapper.column_attrs:
            key = attr.key
            if key.lower() == "id":
                continue
            values[key] = getattr(obj, key, None)
        pending.append((obj, table_name, values))

    # Updates
    for obj in list(session.dirty):
        if isinstance(obj, Logs):
            continue
        if not session.is_modified(obj, include_collections=False):
            continue
        record_id = _get_record_id(obj)
        if record_id is None:
            continue
        table_name = _get_table_name(obj)
        insp = sa_inspect(obj)
        for attr in insp.mapper.column_attrs:
            key = attr.key
            if key.lower() == "id":
                continue
            col_type = None
            try:
                col_type = insp.mapper.columns[key].type
            except Exception:
                col_type = None
            hist = insp.attrs[key].history
            if not hist.has_changes():
                continue
            old_val = hist.deleted[0] if hist.deleted else (hist.unchanged[0] if hist.unchanged else None)
            new_val = hist.added[0] if hist.added else getattr(obj, key, None)
            # Fallback: si l'historique SQLAlchemy ne fournit pas l'ancienne valeur,
            # lire directement dans la BDD avant que le flush n'écrive les changements.
            if (hist.deleted == () or not hist.deleted) and (hist.unchanged == () or not hist.unchanged):
                try:
                    prev = session.execute(
                        text(f'SELECT "{key}" FROM "{table_name}" WHERE id = :id LIMIT 1'),
                        {"id": record_id},
                    ).scalar()
                    old_val = prev
                except Exception:
                    pass
            old_val = _normalize_by_column_type(old_val, col_type) if col_type is not None else old_val
            new_val = _normalize_by_column_type(new_val, col_type) if col_type is not None else new_val

            # Ne rien logger si la valeur ne change pas réellement (après normalisation).
            if _to_str(old_val) == _to_str(new_val):
                continue

            AuditLogger._add_log_row(
                session=session,
                table_name=table_name,
                record_id=record_id,
                operation="UPDATE",
                field_name=key,
                old_value=_to_str(old_val),
                new_value=_to_str(new_val),
            )

    # Deletes
    for obj in list(session.deleted):
        if isinstance(obj, Logs):
            continue
        record_id = _get_record_id(obj)
        if record_id is None:
            continue
        table_name = _get_table_name(obj)
        insp = sa_inspect(obj)
        for attr in insp.mapper.column_attrs:
            key = attr.key
            if key.lower() == "id":
                continue
            col_type = None
            try:
                col_type = insp.mapper.columns[key].type
            except Exception:
                col_type = None
            old_val = getattr(obj, key, None)
            old_val = _normalize_by_column_type(old_val, col_type) if col_type is not None else old_val

            # Ne rien logger si old/new identiques (DELETE => new_value=None).
            if _to_str(old_val) == _to_str(None):
                continue

            AuditLogger._add_log_row(
                session=session,
                table_name=table_name,
                record_id=record_id,
                operation="DELETE",
                field_name=key,
                old_value=_to_str(old_val),
                new_value=None,
            )


def _audit_after_flush(session: Session, flush_context):
    """Log les inserts après flush (IDs disponibles)."""
    pending: List[Tuple[Any, str, Dict[str, Any]]] = session.info.pop("_audit_pending_inserts", [])
    if not pending:
        return

    # Empêcher l'audit de ré-auditer les insertions de logs
    session.info["_audit_logging_disabled"] = True
    try:
        for obj, table_name, values in pending:
            if isinstance(obj, Logs):
                continue
            record_id = _get_record_id(obj)
            if record_id is None:
                # Si on ne peut pas déterminer l'ID, on ignore (cas rare)
                continue
            insp = sa_inspect(obj)
            for key, new_val in values.items():
                col_type = None
                try:
                    col_type = insp.mapper.columns[key].type
                except Exception:
                    col_type = None
                new_val = _normalize_by_column_type(new_val, col_type) if col_type is not None else new_val

                # Ne rien logger si old/new identiques (INSERT => old_value=None).
                if _to_str(None) == _to_str(new_val):
                    continue

                AuditLogger._add_log_row(
                    session=session,
                    table_name=table_name,
                    record_id=record_id,
                    operation="INSERT",
                    field_name=key,
                    old_value=None,
                    new_value=_to_str(new_val),
                )
    finally:
        session.info["_audit_logging_disabled"] = False


class AuditLogger:
    """Gère le contexte d'audit pour les triggers SQLite via une table temporaire.
    
    Les triggers SQLite lisent cette table temporaire pour obtenir le contexte
    utilisateur (email, permissions, source, request_id) et l'injecter dans les logs.
    """
    
    CONTEXT_TABLE = "_audit_context"
    
    @staticmethod
    def _ensure_context_table(session: Session):
        """Crée la table temporaire de contexte si elle n'existe pas."""
        try:
            # Si la session a été rollback, faire un rollback explicite d'abord
            session.rollback()
        except:
            pass  # Ignorer si pas de transaction en cours
        
        try:
            # Vérifier si la table existe déjà en essayant de la lire
            session.execute(text(f"SELECT 1 FROM {AuditLogger.CONTEXT_TABLE} LIMIT 1"))
        except:
            # La table n'existe pas, la créer
            # Pour les tables TEMP dans SQLite, il faut faire un commit après la création
            session.execute(text(f"""
                CREATE TEMP TABLE IF NOT EXISTS {AuditLogger.CONTEXT_TABLE} (
                    user_email TEXT,
                    user_permissions TEXT,
                    source TEXT,
                    request_id TEXT
                )
            """))
            session.commit()  # Commit nécessaire pour que la table TEMP soit accessible
    
    @staticmethod
    def _clear_context_table(session: Session):
        """Vide la table temporaire de contexte."""
        # S'assurer que la table existe avant de la vider
        AuditLogger._ensure_context_table(session)
        try:
            session.execute(text(f"DELETE FROM {AuditLogger.CONTEXT_TABLE}"))
            # Ne pas faire de commit ici, laisser le commit se faire dans l'opération principale
        except:
            # Si la table n'existe pas encore, ignorer
            pass
    
    @staticmethod
    def set_context(
        session: Session,
        user_email: Optional[str] = None,
        user_permissions: Optional[Dict[str, bool]] = None,
        source: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Définit le contexte d'audit pour la session courante.
        
        Args:
            session: Session SQLModel
            user_email: Email de l'utilisateur
            user_permissions: Dict avec is_active, is_validated, is_admin
            source: Source de la modification (ex: "admin/users", "oob/admin")
            request_id: UUID pour tracer une requête complète
        """
        # Contexte côté serveur (pour l'audit basé sur SQLAlchemy)
        session.info["_audit_context"] = {
            "user_email": user_email,
            "user_permissions": json.dumps(user_permissions, ensure_ascii=False) if user_permissions else None,
            "source": source,
            "request_id": request_id,
        }
        AuditLogger._ensure_audit_listeners(session)

        AuditLogger._ensure_context_table(session)
        AuditLogger._clear_context_table(session)
        
        # Sérialiser les permissions en JSON
        permissions_json = None
        if user_permissions:
            permissions_json = json.dumps(user_permissions)
        
        # Insérer le contexte
        session.execute(text(f"""
            INSERT INTO {AuditLogger.CONTEXT_TABLE} (user_email, user_permissions, source, request_id)
            VALUES (:user_email, :user_permissions, :source, :request_id)
        """), {
            "user_email": user_email,
            "user_permissions": permissions_json,
            "source": source,
            "request_id": request_id,
        })
        # Ne pas faire de commit ici, laisser le commit se faire dans l'opération principale

    @staticmethod
    def _ensure_audit_listeners(session: Session):
        """Attache les listeners SQLAlchemy une seule fois par session."""
        if session.info.get("_audit_listeners_attached"):
            return
        event.listen(session, "before_flush", _audit_before_flush)
        event.listen(session, "after_flush", _audit_after_flush)
        session.info["_audit_listeners_attached"] = True

    @staticmethod
    def _add_log_row(
        session: Session,
        table_name: str,
        record_id: int,
        operation: str,
        field_name: str,
        old_value: Optional[str],
        new_value: Optional[str],
    ) -> None:
        """Ajoute une ligne dans la table Logs avec le contexte courant."""
        ctx = session.info.get("_audit_context") or {}
        session.add(
            Logs(
                table_name=table_name,
                record_id=record_id,
                operation=operation,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                changed_at=datetime.now(),
                user_email=ctx.get("user_email"),
                user_permissions=ctx.get("user_permissions"),
                source=ctx.get("source"),
                request_id=ctx.get("request_id"),
            )
        )
    
    @staticmethod
    def set_context_from_user(
        session: Session,
        user: Optional[Users],
        source: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Définit le contexte d'audit à partir d'un objet User.
        
        Args:
            session: Session SQLModel
            user: Objet Users (peut être None pour les opérations système)
            source: Source de la modification
            request_id: UUID pour tracer une requête (généré automatiquement si None)
        """
        user_email = None
        user_permissions = None
        
        if user:
            user_email = user.email
            user_permissions = {
                # Éviter une dépendance à haleon.auth.permissions (risque de circular imports).
                # Les champs sont déjà présents sur le modèle Users.
                "is_active": bool(getattr(user, "is_active", False)),
                "is_validated": bool(getattr(user, "is_validated", False)),
                "is_admin": bool(getattr(user, "is_admin", False)),
            }
        
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        AuditLogger.set_context(
            session=session,
            user_email=user_email,
            user_permissions=user_permissions,
            source=source,
            request_id=request_id,
        )
    
    @staticmethod
    def clear_context(session: Session):
        """Nettoie le contexte d'audit."""
        AuditLogger._clear_context_table(session)
    
    @staticmethod
    def get_context(session: Session) -> Dict[str, Any]:
        """Récupère le contexte d'audit actuel.
        
        Returns:
            Dict avec user_email, user_permissions, source, request_id
        """
        AuditLogger._ensure_context_table(session)
        result = session.execute(text(f"SELECT * FROM {AuditLogger.CONTEXT_TABLE} LIMIT 1"))
        row = result.fetchone()
        
        if row:
            return {
                "user_email": row[0] if row[0] else None,
                "user_permissions": json.loads(row[1]) if row[1] else None,
                "source": row[2] if row[2] else None,
                "request_id": row[3] if row[3] else None,
            }
        return {
            "user_email": None,
            "user_permissions": None,
            "source": None,
            "request_id": None,
        }
    
    @staticmethod
    def with_context(
        session: Session,
        user: Optional[Users] = None,
        source: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Context manager pour gérer automatiquement le contexte d'audit.
        
        Usage:
            with AuditLogger.with_context(session, user, "admin/users"):
                # Opérations CRUD ici
                session.commit()
        """
        return AuditContextManager(session, user, source, request_id)


class AuditContextManager:
    """Context manager pour gérer automatiquement le contexte d'audit."""
    
    def __init__(
        self,
        session: Session,
        user: Optional[Users] = None,
        source: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.session = session
        self.user = user
        self.source = source
        self.request_id = request_id
    
    def __enter__(self):
        AuditLogger.set_context_from_user(
            self.session,
            self.user,
            self.source,
            self.request_id,
        )
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        AuditLogger.clear_context(self.session)
        # Contexte côté serveur
        try:
            self.session.info.pop("_audit_context", None)
        except Exception:
            pass
        return False  # Ne pas supprimer l'exception si elle existe

