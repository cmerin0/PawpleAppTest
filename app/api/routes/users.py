from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.schemas.users import UserCreate, UserRead
from app.services.users import UserEmailAlreadyExistsError, create_user


router = APIRouter(
    prefix="/users",
    tags=["users"],
)

DatabaseSession = Annotated[Session, Depends(get_database_session)]

@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Register a new User account.")
def register_user(user_data: UserCreate, database_session: DatabaseSession) -> UserRead:
    """Register a new User account."""
    try:
        return create_user(database_session, user_data)
    except UserEmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for this email address.",
        ) from error