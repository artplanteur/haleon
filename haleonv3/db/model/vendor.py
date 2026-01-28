from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Vendor(SQLModel, table=True):
    __tablename__ = "vendor"
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, index=True, unique=True)
    description: Optional[str] = Field(default=None)
    portfolio: Optional[str] = Field(default=None, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
