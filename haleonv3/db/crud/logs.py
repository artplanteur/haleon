import logging

from haleonv3.db.model.logs import Logs

logger = logging.getLogger("haleonv3.db.logs")


def log_change(
    session,
    table_name: str,
    record_pk: str,
    field_name: str | None,
    old_value: str | None,
    new_value: str | None,
    request_id: str | None = None,
    source: str | None = None,
    actor_user_id: int | None = None,
    actor_identifier: str | None = None,
    actor_is_active: bool | None = None,
    actor_is_validated: bool | None = None,
    actor_is_admin: bool | None = None,
):
    """Simple DB log: 1 line per field change."""
    log = Logs(
        table_name=table_name,
        record_pk=record_pk,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        request_id=request_id,
        source=source,
        actor_user_id=actor_user_id,
        actor_identifier=actor_identifier,
        actor_is_active=actor_is_active,
        actor_is_validated=actor_is_validated,
        actor_is_admin=actor_is_admin,
        operation="UPDATE",
    )
    session.add(log)
    session.commit()
    logger.info(
        "log_change table=%s pk=%s field=%s",
        table_name,
        record_pk,
        field_name,
    )
