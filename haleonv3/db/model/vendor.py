from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Vendor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, index=True, unique=True)
    description: Optional[str] = Field(default=None)
    portfolio: Optional[str] = Field(default=None, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserVendorAccess(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "vendor_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    access_level: str = Field(default="read", max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserRole(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "app", "role"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    app: str = Field(max_length=50, index=True)
    role: str = Field(max_length=20, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
