from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import Pet, PetDismissal, PetStatus
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

    for field_name, value in pet_data.model_dump(exclude_unset=True).items():
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
    pet.published_at = datetime.now(UTC)

    database_session.commit()
    database_session.refresh(pet)

    return pet


# list_available_pets retrieves a paginated list of Pets that are currently available for adoption.
def list_available_pets(
    database_session: Session,
    *,
    offset: int,
    limit: int,
    current_user_id: UUID | None = None,
) -> list[Pet]:
    statement = select(Pet).where(
        Pet.status == PetStatus.AVAILABLE,
    )

    if current_user_id is not None:
        dismissal_exists = (
            select(PetDismissal.pet_id)
            .where(
                PetDismissal.user_id == current_user_id,
                PetDismissal.pet_id == Pet.id,
            )
            .exists()
        )
        statement = statement.where(~dismissal_exists)

    statement = statement.order_by(Pet.published_at.desc()).offset(offset).limit(limit)

    return list(database_session.scalars(statement).all())


# get_available_pet retrieves a Pet by its ID, but only
# if it is currently available for adoption.
def get_available_pet(
    database_session: Session,
    *,
    pet_id: UUID,
    current_user_id: UUID | None = None,
) -> Pet:
    statement = select(Pet).where(
        Pet.id == pet_id,
        Pet.status == PetStatus.AVAILABLE,
    )

    if current_user_id is not None:
        dismissal_exists = (
            select(PetDismissal.pet_id)
            .where(
                PetDismissal.user_id == current_user_id,
                PetDismissal.pet_id == Pet.id,
            )
            .exists()
        )
        statement = statement.where(~dismissal_exists)

    pet = database_session.scalar(statement)

    if pet is None:
        raise PetNotFoundError

    return pet


def dismiss_available_pet(
    database_session: Session,
    *,
    user_id: UUID,
    pet_id: UUID,
) -> None:
    get_available_pet(
        database_session,
        pet_id=pet_id,
    )

    existing_dismissal = database_session.get(
        PetDismissal,
        {
            "user_id": user_id,
            "pet_id": pet_id,
        },
    )

    if existing_dismissal is not None:
        return

    dismissal = PetDismissal(
        user_id=user_id,
        pet_id=pet_id,
    )
    database_session.add(dismissal)

    try:
        database_session.commit()
    except IntegrityError:
        database_session.rollback()

        existing_dismissal = database_session.get(
            PetDismissal,
            {
                "user_id": user_id,
                "pet_id": pet_id,
            },
        )

        if existing_dismissal is None:
            raise
