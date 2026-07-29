from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Safe representation of a stored pet photo."""
class PetPhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    alt_text: str
    sort_order: int
    created_at: datetime
