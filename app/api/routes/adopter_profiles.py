from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_database_session
from app.schemas.adopter_profiles import (
    AdopterProfileCreate,
    AdopterProfileRead,
    AdopterProfileUpdate,
)
from app.services.adopter_profiles import (
    AdopterProfileAlreadyExistsError,
    AdopterProfileNotFoundError,
    create_adopter_profile,
    get_adopter_profile_for_user,
    update_adopter_profile,
)

router = APIRouter(
    prefix="/adopter-profile",
    tags=["adopter profile"],
)

DatabaseSession = Annotated[Session, Depends(get_database_session)]


# The following endpoints allow an authenticated User
# to create, read, and update their AdopterProfile.
@router.post(
    "",
    response_model=AdopterProfileRead,
    status_code=status.HTTP_201_CREATED,
)
def create_current_users_adopter_profile(
    profile_data: AdopterProfileCreate,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> AdopterProfileRead:
    try:
        profile = create_adopter_profile(
            database_session,
            user=current_user,
            profile_data=profile_data,
        )
    except AdopterProfileAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The current user already has an adopter profile.",
        ) from error

    return AdopterProfileRead.model_validate(profile)


# The following endpoints allow an authenticated User
# to read and update their AdopterProfile.
@router.get("/me", response_model=AdopterProfileRead)
def read_current_users_adopter_profile(
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> AdopterProfileRead:
    """Return the authenticated User's AdopterProfile."""
    try:
        profile = get_adopter_profile_for_user(
            database_session,
            user=current_user,
        )
    except AdopterProfileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adopter profile not found.",
        ) from error

    return AdopterProfileRead.model_validate(profile)


# The following endpoint allows an authenticated User
# to update their AdopterProfile.
@router.patch("/me", response_model=AdopterProfileRead)
def update_current_users_adopter_profile(
    profile_data: AdopterProfileUpdate,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> AdopterProfileRead:
    """Update the authenticated User's AdopterProfile."""
    try:
        profile = get_adopter_profile_for_user(
            database_session,
            user=current_user,
        )
    except AdopterProfileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adopter profile not found.",
        ) from error

    updated_profile = update_adopter_profile(
        database_session,
        profile=profile,
        profile_data=profile_data,
    )

    return AdopterProfileRead.model_validate(updated_profile)
