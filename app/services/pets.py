from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Pet, PetStatus
from app.schemas.pets import PetCreate, PetUpdate


class PetNotFoundError(Exception):
    """Raised when a Pet cannot be found in the expected Shelter."""


class PetStateConflictError(Exception):
    """Raised when a Pet cannot transition from its current status."""

# Functions for managing Pet entities in the database, 
# including creation, retrieval, updating, and publishing of pet listings. 
# These functions enforce business rules such as ownership and status transitions.

# create_pet creates a new draft Pet for a specific Shelter,
def create_pet(
    database_session: Session,
    *,
    shelter_id: UUID,
    pet_data: PetCreate,
) -> Pet:
    """Create a draft Pet for one Shelter."""
    pet = Pet(
        shelter_id=shelter_id,
        name=pet_data.name,
        species=pet_data.species,
        breed=pet_data.breed,
        sex=pet_data.sex,
        birth_date=pet_data.birth_date,
        size=pet_data.size,
        description=pet_data.description,
        status=PetStatus.DRAFT,
    )

    database_session.add(pet)
    database_session.commit()
    database_session.refresh(pet)

    return pet

# get_shelter_pet retrieves a Pet by its ID, ensuring it belongs to the specified Shelter.
def get_shelter_pet(
    database_session: Session,
    *,
    shelter_id: UUID,
    pet_id: UUID,
) -> Pet:
    """Return one Pet only when it belongs to the requesting Shelter."""
    statement = select(Pet).where(
        Pet.id == pet_id,
        Pet.shelter_id == shelter_id,
    )
    pet = database_session.scalar(statement)

    if pet is None:
        raise PetNotFoundError

    return pet

# update_draft_pet updates the details of a Pet, but only if it is still in the draft state.
def update_draft_pet(
    database_session: Session,
    *,
    pet: Pet,
    pet_data: PetUpdate,
) -> Pet:
    """Update a Pet only while it remains a draft."""
    if pet.status is not PetStatus.DRAFT:
        raise PetStateConflictError

    for field_name, value in pet_data.model_dump(
        exclude_unset=True
    ).items():
        setattr(pet, field_name, value)

    database_session.commit()
    database_session.refresh(pet)

    return pet

# publish_pet transitions a draft Pet to the available state, making it publicly discoverable.
def publish_pet(
    database_session: Session,
    *,
    pet: Pet,
) -> Pet:
    """Publish a draft Pet to public discovery."""
    if pet.status is not PetStatus.DRAFT:
        raise PetStateConflictError

    pet.status = PetStatus.AVAILABLE
    pet.published_at = datetime.now(timezone.utc)

    database_session.commit()
    database_session.refresh(pet)

    return pet

# list_available_pets retrieves a paginated list of Pets that are currently available for adoption.
def list_available_pets(
    database_session: Session,
    *,
    offset: int,
    limit: int,
) -> list[Pet]:
    """Return publicly discoverable Pet listings."""
    statement = (
        select(Pet)
        .where(Pet.status == PetStatus.AVAILABLE)
        .order_by(Pet.published_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(database_session.scalars(statement).all())

# get_available_pet retrieves a Pet by its ID, but only if it is currently available for adoption.
def get_available_pet(
    database_session: Session,
    *,
    pet_id: UUID,
) -> Pet:
    """Return a Pet only when it is publicly available."""
    statement = select(Pet).where(
        Pet.id == pet_id,
        Pet.status == PetStatus.AVAILABLE,
    )
    pet = database_session.scalar(statement)

    if pet is None:
        raise PetNotFoundError

    return pet