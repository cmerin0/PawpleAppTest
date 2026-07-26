from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.entities import PetStatus

# Pydantic models for Pet-related data transfer objects (DTOs) 
# used in API requests and responses.
class PetCreate(BaseModel):

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    species: str = Field(min_length=1, max_length=40)
    breed: str | None = Field(default=None, max_length=100)
    sex: str | None = Field(default=None, max_length=20)
    birth_date: date | None = None
    size: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=5_000)

    @field_validator("birth_date")
    @classmethod
    def birth_date_cannot_be_in_the_future(
        cls,
        value: date | None,
    ) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Birth date cannot be in the future.")

        return value

# The PetCreate model defines the fields required to create a new pet listing,
# including validation rules for each field. The birth_date field has a custom
# validator to ensure that the date is not set in the future.
class PetUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    species: str | None = Field(default=None, min_length=1, max_length=40)
    breed: str | None = Field(default=None, max_length=100)
    sex: str | None = Field(default=None, max_length=20)
    birth_date: date | None = None
    size: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=5_000)

    @field_validator("birth_date")
    @classmethod
    def birth_date_cannot_be_in_the_future(
        cls,
        value: date | None,
    ) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Birth date cannot be in the future.")

        return value

# The PetUpdate model defines the fields that can be updated for an existing pet listing.
class PetRead(BaseModel):
    
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shelter_id: UUID
    name: str
    species: str
    breed: str | None
    sex: str | None
    birth_date: date | None
    size: str | None
    description: str | None
    status: PetStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime