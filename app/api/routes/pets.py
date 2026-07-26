from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.shelter import CurrentShelterManager
from app.db.session import get_database_session
from app.schemas.pets import PetCreate, PetRead, PetUpdate
from app.services.pets import (
    PetNotFoundError,
    PetStateConflictError,
    create_pet,
    get_available_pet,
    get_shelter_pet,
    list_available_pets,
    publish_pet,
    update_draft_pet,
)


DatabaseSession = Annotated[Session, Depends(get_database_session)]

public_router = APIRouter(
    prefix="/pets",
    tags=["pets"],
)

shelter_router = APIRouter(
    prefix="/shelter/pets",
    tags=["shelter pets"],
)

# Public endpoints for listing and reading available pets, 
# and shelter endpoints for creating, updating, and publishing pets.
@public_router.get(
    "",
    response_model=list[PetRead],
)
def list_pets(
    database_session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[PetRead]:
    pets = list_available_pets(
        database_session,
        offset=offset,
        limit=limit,
    )

    return [PetRead.model_validate(pet) for pet in pets]

# read_pet retrieves a single pet by its ID, but only if it is currently available for adoption.
@public_router.get(
    "/{pet_id}",
    response_model=PetRead,
)
def read_pet(
    pet_id: UUID,
    database_session: DatabaseSession,
) -> PetRead:
    """Read one publicly available Pet."""
    try:
        pet = get_available_pet(
            database_session,
            pet_id=pet_id,
        )
    except PetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found.",
        ) from error

    return PetRead.model_validate(pet)

# Shelter endpoints for creating, updating, and publishing pets,
# which require the user to have a shelter membership with owner or manager role.
@shelter_router.post(
    "",
    response_model=PetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_shelter_pet(
    pet_data: PetCreate,
    membership: CurrentShelterManager,
    database_session: DatabaseSession,
) -> PetRead:
    """Create a draft Pet for the current manager's Shelter."""
    pet = create_pet(
        database_session,
        shelter_id=membership.shelter_id,
        pet_data=pet_data,
    )

    return PetRead.model_validate(pet)

# update_shelter_pet updates the details of a draft pet belonging to the current shelter,
# but only if the pet is still in the draft state.
@shelter_router.patch(
    "/{pet_id}",
    response_model=PetRead,
)
def update_shelter_pet(
    pet_id: UUID,
    pet_data: PetUpdate,
    membership: CurrentShelterManager,
    database_session: DatabaseSession,
) -> PetRead:
    """Update one draft Pet belonging to the current Shelter."""
    try:
        pet = get_shelter_pet(
            database_session,
            shelter_id=membership.shelter_id,
            pet_id=pet_id,
        )
        updated_pet = update_draft_pet(
            database_session,
            pet=pet,
            pet_data=pet_data,
        )
    except PetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found.",
        ) from error
    except PetStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft pets can be updated.",
        ) from error

    return PetRead.model_validate(updated_pet)

# publish_shelter_pet transitions a draft pet to the available state, making it publicly discoverable,
# but only if the pet belongs to the current shelter and is still in the draft state.
@shelter_router.post(
    "/{pet_id}/publish",
    response_model=PetRead,
)
def publish_shelter_pet(
    pet_id: UUID,
    membership: CurrentShelterManager,
    database_session: DatabaseSession,
) -> PetRead:
    """Publish one draft Pet from the current Shelter."""
    try:
        pet = get_shelter_pet(
            database_session,
            shelter_id=membership.shelter_id,
            pet_id=pet_id,
        )
        published_pet = publish_pet(
            database_session,
            pet=pet,
        )
    except PetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found.",
        ) from error
    except PetStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft pets can be published.",
        ) from error

    return PetRead.model_validate(published_pet)