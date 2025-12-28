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
    last_connection: Optional[datetime] = Field(default=None)
    country: Optional[str] = None  # Ajouté pour correspondre aux claims SSO











