from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdopterProfileCreate(BaseModel):
    """Data accepted when a User creates an AdopterProfile."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )


class AdopterProfileUpdate(BaseModel):
    """Data an authenticated User may change on their AdopterProfile."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )


class AdopterProfileRead(BaseModel):
    """Safe AdopterProfile data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    phone: str | None
    created_at: datetime
    updated_at: datetime
