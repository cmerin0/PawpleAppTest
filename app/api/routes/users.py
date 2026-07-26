from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_database_session
from app.schemas.users import UserCreate, UserRead, UserUpdate
from app.services.users import UserEmailAlreadyExistsError, create_user, delete_user, update_user

router = APIRouter(prefix="/users", tags=["users"])

# Define a type alias for a database session dependency, which will be injected into route handlers.
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new User account.",
)
def register_user(user_data: UserCreate, database_session: DatabaseSession) -> UserRead:
    """Register a new User account."""
    try:
        created_user = create_user(database_session, user_data)
        return UserRead.model_validate(created_user)
    except UserEmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for this email address.",
        ) from error


@router.get("/me", response_model=UserRead, summary="Get the authenticated User's account data.")
def read_current_user(current_user: CurrentUser) -> UserRead:
    """Return the authenticated User's safe account data."""
    return UserRead.model_validate(current_user)


@router.patch(
    "/me", response_model=UserRead, summary="Update the authenticated User's account data."
)
def update_current_user(
    user_data: UserUpdate, current_user: CurrentUser, database_session: DatabaseSession
) -> UserRead:
    """Update the authenticated User's allowed profile fields."""
    updated_user = update_user(database_session, current_user, user_data)
    return UserRead.model_validate(updated_user)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete the authenticated User's account.",
)
def delete_current_user(current_user: CurrentUser, database_session: DatabaseSession) -> Response:
    """Permanently delete the authenticated User's account."""
    delete_user(database_session, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
