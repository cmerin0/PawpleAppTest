from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_database_session
from app.schemas.auth import AccessToken, LoginRequest
from app.services.users import authenticate_user

router = APIRouter(prefix="/auth", tags=["authentication"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("/login", response_model=AccessToken)
def login(login_data: LoginRequest, database_session: DatabaseSession) -> AccessToken:
    """Authenticate a User and return a short-lived access token."""
    user = authenticate_user(database_session, login_data)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AccessToken(access_token=create_access_token(str(user.id)))
