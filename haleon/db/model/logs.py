"""Modèle de table Logs pour l'audit de la base de données."""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Logs(SQLModel, table=True):
    """Modèle de table Logs pour enregistrer tous les changements dans la base de données.
    
    Une entrée par champ modifié, permettant de tracer précisément chaque modification.
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    table_name: str = Field(index=True, description="Nom de la table modifiée")
    record_id: int = Field(index=True, description="ID de l'enregistrement modifié")
    operation: str = Field(description="Type d'opération: INSERT, UPDATE, DELETE")
    field_name: str = Field(description="Nom du champ modifié")
    old_value: Optional[str] = Field(default=None, description="Valeur avant modification (JSON)")
    new_value: Optional[str] = Field(default=None, description="Valeur après modification (JSON)")
    changed_at: datetime = Field(default_factory=datetime.now, index=True, description="Timestamp du changement")
    user_email: Optional[str] = Field(default=None, index=True, description="Email de l'utilisateur ayant effectué le changement")
    user_permissions: Optional[str] = Field(default=None, description="Permissions de l'utilisateur au moment du changement (JSON)")
    source: Optional[str] = Field(default=None, description="Source de la modification: web, api, migration, etc.")
    request_id: Optional[str] = Field(default=None, index=True, description="UUID pour tracer une requête complète")


