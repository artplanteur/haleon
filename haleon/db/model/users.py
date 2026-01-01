"""Modèle de table Users pour la gestion des utilisateurs."""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Users(SQLModel, table=True):
    """Modèle de table Users pour la gestion des utilisateurs."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    family_name: Optional[str] = None
    first_name: Optional[str] = None
    session_id: Optional[str] = None
    is_connected: bool = Field(default=False)
    is_validated: bool = Field(default=False)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    # Legacy (kept for backward compatibility with existing DBs; no longer used by auth).
    last_connection: Optional[datetime] = Field(default=None)

    # Auth timestamps
    # - last_login_at: set on successful login
    # - last_seen_at: updated on each authenticated mount/request (activity heartbeat)
    # - updated_at: set on any CRUD update to the user row
    last_login_at: Optional[datetime] = Field(default=None)
    last_seen_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    country: Optional[str] = None  # Ajouté pour correspondre aux claims SSO











