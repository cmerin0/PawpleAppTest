from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, OptionalCurrentUser
from app.api.dependencies.shelter import CurrentShelterManager
from app.db.session import get_database_session
from app.schemas.pets import PetCreate, PetRead, PetUpdate
from app.services.pets import (
    PetNotFoundError,
    PetStateConflictError,
    create_pet,
    dismiss_available_pet,
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


# list_pets retrieves a paginated list of available pets, excluding the current user's dismissals.
@public_router.get(
    "",
    response_model=list[PetRead],
)
def list_pets(
    database_session: DatabaseSession,
    current_user: OptionalCurrentUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[PetRead]:
    pets = list_available_pets(
        database_session,
        offset=offset,
        limit=limit,
        current_user_id=(current_user.id if current_user is not None else None),
    )

    return [PetRead.model_validate(pet) for pet in pets]



# Read endpoint for retrieving a single available pet by its ID.
# This endpoint returns a 404 error if the pet is not found or is not available.
@public_router.get(
    "/{pet_id}",
    response_model=PetRead,
)
def read_pet(
    pet_id: UUID,
    database_session: DatabaseSession,
    current_user: OptionalCurrentUser,
) -> PetRead:
    try:
        pet = get_available_pet(
            database_session,
            pet_id=pet_id,
            current_user_id=(current_user.id if current_user is not None else None),
        )
    except PetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found.",
        ) from error

    return PetRead.model_validate(pet)


# Dismissal endpoint for marking a pet as dismissed by the authenticated user.
# This endpoint returns a 404 error if the pet is not found or is not available.
@public_router.put(
    "/{pet_id}/dismissal",
    status_code=status.HTTP_204_NO_CONTENT,
)
def dismiss_pet(
    pet_id: UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> Response:
    """Record that the authenticated User is not interested in one Pet."""
    try:
        dismiss_available_pet(
            database_session,
            user_id=current_user.id,
            pet_id=pet_id,
        )
    except PetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found.",
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


# publish_shelter_pet transitions a draft pet to the available state,
# making it publicly discoverable, but only if pet belongs to the current shelter
# and is still in the draft state.
@shelter_router.post(
    "/{pet_id}/publish",
    response_model=PetRead,
)
def publish_shelter_pet(
    pet_id: UUID,
    membership: CurrentShelterManager,
    database_session: DatabaseSession,
) -> PetRead:
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
