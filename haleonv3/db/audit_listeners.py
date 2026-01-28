"""Centralized SQLAlchemy audit logging.

Registers ORM events to automatically write row-level field change logs
into the `logs` table (see `haleonv3.db.model.logs.Logs`).
"""

from __future__ import annotations

from sqlalchemy import event, inspect
from sqlmodel import Session

from haleonv3.db.model.logs import Logs

# Avoid logging noisy and/or sensitive fields by default.
# Adjust as needed.
_DENY_FIELDS = {
    "updated_at",
    "session_id",
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "secret",
}


@event.listens_for(Session, "before_flush")
def _audit_before_flush(session: Session, flush_context, instances) -> None:  # noqa: ANN001
    """Capture pending INSERT/UPDATE/DELETE operations for audit logging.

    Notes:
    - INSERT logs are created in `after_flush` so we can capture the DB-assigned PK.
    - UPDATE/DELETE logs are created here (PK already known).
    - We do NOT commit inside listeners. Logs are committed with the business transaction.
    - Actor/context can be passed via session.info["actor"] (dict).
    """

    actor = session.info.get("actor") or {}

    # Store INSERT candidates for after_flush (so PK is available).
    session.info["_audit_new"] = [
        obj for obj in session.new if not isinstance(obj, Logs)
    ]

    for obj in session.dirty:
        # Prevent recursion / noise: never log changes to the Logs table itself.
        if isinstance(obj, Logs):
            continue

        state = inspect(obj)
        if not state.modified:
            continue

        # Only column attributes (no relationships).
        for col_attr in state.mapper.column_attrs:
            key = col_attr.key
            if key in _DENY_FIELDS:
                continue

            hist = state.attrs[key].history
            if not hist.has_changes():
                continue

            old = hist.deleted[0] if hist.deleted else None
            new = hist.added[0] if hist.added else getattr(obj, key, None)

            record_pk = ""
            if state.identity:
                # Common case: single-column PK.
                record_pk = str(state.identity[0])

            session.add(
                Logs(
                    table_name=getattr(obj, "__tablename__", obj.__class__.__name__),
                    record_pk=record_pk,
                    field_name=key,
                    old_value=None if old is None else str(old),
                    new_value=None if new is None else str(new),
                    operation="UPDATE",
                    request_id=actor.get("request_id"),
                    source=actor.get("source"),
                    actor_user_id=actor.get("user_id"),
                    actor_identifier=actor.get("identifier"),
                    actor_is_active=actor.get("is_active"),
                    actor_is_validated=actor.get("is_validated"),
                    actor_is_admin=actor.get("is_admin"),
                )
            )

    for obj in session.deleted:
        if isinstance(obj, Logs):
            continue

        state = inspect(obj)
        record_pk = ""
        if state.identity:
            record_pk = str(state.identity[0])

        # Log all columns on DELETE (except denylist).
        for col_attr in state.mapper.column_attrs:
            key = col_attr.key
            if key in _DENY_FIELDS:
                continue

            old_val = getattr(obj, key, None)
            session.add(
                Logs(
                    table_name=getattr(obj, "__tablename__", obj.__class__.__name__),
                    record_pk=record_pk,
                    field_name=key,
                    old_value=None if old_val is None else str(old_val),
                    new_value=None,
                    operation="DELETE",
                    request_id=actor.get("request_id"),
                    source=actor.get("source"),
                    actor_user_id=actor.get("user_id"),
                    actor_identifier=actor.get("identifier"),
                    actor_is_active=actor.get("is_active"),
                    actor_is_validated=actor.get("is_validated"),
                    actor_is_admin=actor.get("is_admin"),
                )
            )


@event.listens_for(Session, "after_flush")
def _audit_after_flush(session: Session, flush_context) -> None:  # noqa: ANN001
    """Create INSERT logs after flush (PK is available)."""

    actor = session.info.get("actor") or {}
    new_objs = session.info.pop("_audit_new", [])
    if not new_objs:
        return

    for obj in new_objs:
        # Should already be filtered, but keep it explicit.
        if isinstance(obj, Logs):
            continue

        state = inspect(obj)
        record_pk = ""
        if state.identity:
            record_pk = str(state.identity[0])

        # Log all columns on INSERT (except denylist).
        for col_attr in state.mapper.column_attrs:
            key = col_attr.key
            if key in _DENY_FIELDS:
                continue

            new_val = getattr(obj, key, None)
            session.add(
                Logs(
                    table_name=getattr(obj, "__tablename__", obj.__class__.__name__),
                    record_pk=record_pk,
                    field_name=key,
                    old_value=None,
                    new_value=None if new_val is None else str(new_val),
                    operation="INSERT",
                    request_id=actor.get("request_id"),
                    source=actor.get("source"),
                    actor_user_id=actor.get("user_id"),
                    actor_identifier=actor.get("identifier"),
                    actor_is_active=actor.get("is_active"),
                    actor_is_validated=actor.get("is_validated"),
                    actor_is_admin=actor.get("is_admin"),
                )
            )

