"""Modèles SQLModel pour l'application OOB."""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import pytz

swiss_tz = pytz.timezone("Europe/Zurich")


class OOBVendor(SQLModel, table=True):
    """Modèle de table Vendor pour OOB.
    
    Table: app_OOB_Vendor
    """
    __tablename__ = "app_OOB_Vendor"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, unique=True, index=True, description="Code vendor (max 10 caractères)")
    description: Optional[str] = Field(default=None, description="Description du vendor")


class OOBComment(SQLModel, table=True):
    """Modèle de table Comment pour OOB.
    
    Table: app_OOB_Comment
    """
    __tablename__ = "app_OOB_Comment"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    doc_ext: str = Field(index=True, description="Numéro de PO (Purchase Order)")
    username: str = Field(description="Email de l'utilisateur SSO")
    comment: str = Field(description="Contenu du commentaire")
    created_at: datetime = Field(default_factory=lambda: datetime.now(swiss_tz))
    updated_at: Optional[datetime] = Field(default=None, description="Date de dernière modification")


class OOBUserVendorAccess(SQLModel, table=True):
    """Modèle de table UserVendorAccess pour OOB.
    
    Table: app_OOB_UserVendorAccess
    Gère les accès utilisateur-vendor.
    """
    __tablename__ = "app_OOB_UserVendorAccess"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", description="ID de l'utilisateur")
    vendor_id: int = Field(foreign_key="app_OOB_Vendor.id", description="ID du vendor")
    granted_by: Optional[int] = Field(default=None, foreign_key="users.id", description="ID de l'admin qui a accordé l'accès")
    created_at: datetime = Field(default_factory=lambda: datetime.now(swiss_tz))
    
    # Unique constraint sur (user_id, vendor_id)
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )









