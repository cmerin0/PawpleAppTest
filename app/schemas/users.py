from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Data accepted when a visitor registers a new account."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class UserUpdate(BaseModel):
    """Data an existing user may change through the general update endpoint."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    display_name: str | None = Field(default=None, min_length=1, max_length=120)


class UserRead(BaseModel):
    """Safe User data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str
    is_platform_admin: bool
    created_at: datetime
    updated_at: datetime