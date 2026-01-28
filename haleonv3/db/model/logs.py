from datetime import datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class Logs(SQLModel, table=True):
    # Make the table name explicit (easier for beginners + avoids surprises).
    __tablename__ = "logs"

    # Helpful indexes for typical audit queries.
    __table_args__ = (
        Index("ix_logs_changed_at", "changed_at"),
        Index("ix_logs_table_record_changed_at", "table_name", "record_pk", "changed_at"),
        Index("ix_logs_request_id", "request_id"),
        Index("ix_logs_actor_identifier", "actor_identifier"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    changed_at: datetime = Field(default_factory=datetime.utcnow)

    request_id: Optional[str] = Field(default=None)
    source: Optional[str] = Field(default=None)

    actor_user_id: Optional[int] = Field(default=None, index=True)
    actor_identifier: Optional[str] = Field(default=None)
    actor_is_active: Optional[bool] = Field(default=None)
    actor_is_validated: Optional[bool] = Field(default=None)
    actor_is_admin: Optional[bool] = Field(default=None)

    operation: str = Field(default="UPDATE", max_length=10)
    table_name: str = Field(max_length=100)
    record_pk: str = Field(max_length=100)
    field_name: Optional[str] = Field(default=None, max_length=100)
    old_value: Optional[str] = Field(default=None)
    new_value: Optional[str] = Field(default=None)
