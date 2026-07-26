from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_database_session
from app.models.entities import User

bearer_scheme = HTTPBearer(auto_error=False)

DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_credentials_exception() -> HTTPException:
    """Return the standard authentication error used by protected endpoints."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_optional_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    database_session: DatabaseSession,
) -> User | None:
    """Return a User for a valid token, or None when no token was sent."""
    if credentials is None:
        return None

    if credentials.scheme.lower() != "bearer":
        raise get_credentials_exception()

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")

        if not isinstance(subject, str):
            raise get_credentials_exception()

        user_id = UUID(subject)
    except (InvalidTokenError, ValueError, TypeError) as error:
        raise get_credentials_exception() from error

    user = database_session.get(User, user_id)

    if user is None:
        raise get_credentials_exception()

    return user


def get_current_user(
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> User:
    """Return the User identified by a valid Bearer token."""
    if current_user is None:
        raise get_credentials_exception()

    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]

OptionalCurrentUser = Annotated[
    User | None,
    Depends(get_optional_current_user),
]
