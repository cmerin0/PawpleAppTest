from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_database_session
from app.schemas.shelters import ShelterCreate, ShelterRead
from app.services.shelters import (
    ShelterSlugAlreadyExistsError,
    UserAlreadyBelongsToShelterError,
    get_shelter_for_user,
)
from app.services.shelters import (
    create_shelter as create_shelter_record,
)

router = APIRouter(prefix="/shelters", tags=["shelters"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


# Endpoint to create a new Shelter and assign the current user as its owner.
@router.post("", response_model=ShelterRead, status_code=status.HTTP_201_CREATED)
def create_shelter(
    shelter_data: ShelterCreate,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> ShelterRead:
    try:
        shelter = create_shelter_record(
            database_session,
            owner=current_user,
            shelter_data=shelter_data,
        )
    except UserAlreadyBelongsToShelterError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user can belong to only one shelter.",
        ) from error
    except ShelterSlugAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shelter already exists for this slug.",
        ) from error

    return ShelterRead.model_validate(shelter)


# Endpoint to retrieve the Shelter associated with the currently authenticated user.
@router.get("/me", response_model=ShelterRead)
def read_current_users_shelter(
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> ShelterRead:
    shelter = get_shelter_for_user(
        database_session,
        user_id=current_user.id,
    )

    if shelter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The current user does not belong to a shelter.",
        )

    return ShelterRead.model_validate(shelter)
