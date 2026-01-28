from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class UserVendorAccess(SQLModel, table=True):
    """OOB-only table: per-user access level per vendor.

    access_level values:
    - "read"
    - "write"
    - absence of row = "none"
    """

    __tablename__ = "user_vendor_access"
    __table_args__ = (UniqueConstraint("user_id", "vendor_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    access_level: str = Field(default="read", max_length=10)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

