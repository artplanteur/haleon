"""Modèle de table de liaison pour gérer les permissions utilisateur ↔ application."""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import UniqueConstraint


class UserApplicationAccess(SQLModel, table=True):
    """Modèle de table de liaison pour gérer les permissions utilisateur ↔ application."""
    
    __table_args__ = (
        UniqueConstraint('user_id', 'application_id', name='unique_user_app_access'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    granted_at: datetime = Field(default_factory=datetime.now)
    granted_by: Optional[int] = Field(foreign_key="users.id", default=None)  # Admin qui a accordé











