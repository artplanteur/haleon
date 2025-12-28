"""Modèle de table Applications pour stocker les applications disponibles."""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Applications(SQLModel, table=True):
    """Modèle de table Applications pour stocker les applications disponibles."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # "App 1", "App 2", etc. (affiché dans la navbar)
    code: str = Field(unique=True, index=True)  # "app1", "app2" (pour les routes)
    description: Optional[str] = None
    route: str  # "/apps/app1", "/apps/app2" (correspond au chemin physique apps/)
    icon: Optional[str] = None  # Emoji ou nom d'icône
    is_active: bool = Field(default=True)  # Pour désactiver une app
    minimum_requirement: str = Field(default="validated")  # "active", "validated", ou "admin"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None











