from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Safe representation of a stored pet photo.
class PetPhotoRead(BaseModel):
    """
    Private representation of a pet photo.

    The permanent MinIO object key remains private.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    alt_text: str
    sort_order: int
    created_at: datetime


class PetPhotoPublicRead(BaseModel):
    """
    Public representation of a pet photo.

    The permanent MinIO object key remains private. Clients receive only
    a short-lived URL generated for the current request.
    """

    id: UUID
    pet_id: UUID
    alt_text: str
    sort_order: int
    created_at: datetime
    url: str
