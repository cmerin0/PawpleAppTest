import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# The ShelterCreate model is used to validate and normalize data when creating a new shelter.
class ShelterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=3, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=2, max_length=2)

    # Validators to normalize and validate the slug and state fields
    # The slug is converted to lowercase and checked against a regex pattern
    # to ensure it only contains lowercase letters, numbers, and single hyphens.
    # The state is converted to uppercase and checked to ensure it consists of two letters.
    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        normalized = value.lower()

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalized):
            raise ValueError("Slug must contain lowercase letters, numbers, and single hyphens.")

        return normalized

    # Validator to normalize the state field to uppercase and ensure it consists of two letters.
    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        normalized = value.upper()

        if not normalized.isalpha():
            raise ValueError("State must contain two letters.")

        return normalized


# The ShelterRead model is used to return safe Shelter data from the API.
class ShelterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    email: EmailStr
    phone: str | None
    city: str
    state: str
    created_at: datetime
    updated_at: datetime
