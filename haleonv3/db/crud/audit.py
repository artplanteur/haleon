from typing import Any, Iterable

from haleonv3.db.crud.logs import log_change


def log_model_changes(
    session,
    table_name: str,
    record_pk: str,
    before: dict,
    after: dict,
    fields: Iterable[str],
    request_id: str | None = None,
    source: str | None = None,
    actor_user_id: int | None = None,
    actor_identifier: str | None = None,
    actor_is_active: bool | None = None,
    actor_is_validated: bool | None = None,
    actor_is_admin: bool | None = None,
):
    """Log 1 row per changed field using a simple before/after dict."""
    for field in fields:
        old_val = before.get(field)
        new_val = after.get(field)
        if old_val != new_val:
            log_change(
                session=session,
                table_name=table_name,
                record_pk=record_pk,
                field_name=field,
                old_value=_to_str(old_val),
                new_value=_to_str(new_val),
                request_id=request_id,
                source=source,
                actor_user_id=actor_user_id,
                actor_identifier=actor_identifier,
                actor_is_active=actor_is_active,
                actor_is_validated=actor_is_validated,
                actor_is_admin=actor_is_admin,
            )


def _to_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
