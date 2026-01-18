from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Users(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    immutable_id: str = Field(max_length=20, index=True, unique=True)

    email: Optional[str] = Field(default=None)
    first_name: Optional[str] = Field(default=None)
    family_name: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)

    is_active: bool = Field(default=False)
    is_validated: bool = Field(default=False)
    is_admin: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = Field(default=None)
