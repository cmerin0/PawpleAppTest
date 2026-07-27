from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import AdoptionApplicationStatus


# Adoption application schemas for creating, updating, and reading adoption applications.
class AdoptionApplicationDraftUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    contact_phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )
    message: str | None = Field(
        default=None,
        min_length=1,
        max_length=2_000,
    )


# Information required to submit an adoption application, including contact details and consent.
class AdoptionApplicationSubmit(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    contact_phone: str = Field(
        min_length=7,
        max_length=30,
    )
    message: str = Field(
        min_length=1,
        max_length=2_000,
    )
    consent: Literal[True]


# Safe application data returned to its applicant.
class AdoptionApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    applicant_user_id: UUID
    status: AdoptionApplicationStatus
    contact_phone: str | None
    message: str | None
    consent_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime

# Additional application data returned to shelter staff, 
# including the applicant's display name.
class ShelterApplicationRead(AdoptionApplicationRead):

    applicant_display_name: str

# A normal review-status change made by a shelter owner or manager.
class ShelterApplicationStatusUpdate(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    status: Literal[
        AdoptionApplicationStatus.REVIEWING,
        AdoptionApplicationStatus.CONTACTED,
        AdoptionApplicationStatus.REJECTED,
    ]
    note: str | None = Field(
        default=None,
        max_length=1_000,
    )

# Optional context recorded when a shelter approves an application
class ShelterApplicationApproval(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    note: str | None = Field(
        default=None,
        max_length=1_000,
    )