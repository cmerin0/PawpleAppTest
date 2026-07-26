from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.entities import User
from app.schemas.auth import LoginRequest
from app.schemas.users import UserCreate, UserUpdate


class UserEmailAlreadyExistsError(Exception):
    """Raised when an email address is already registered."""


def create_user(database_session: Session, user_data: UserCreate) -> User:
    """Create a user with a securely hashed password."""
    user = User(
        email=str(user_data.email).lower(),
        password_hash=hash_password(user_data.password),
        display_name=user_data.display_name,
    )

    database_session.add(user)

    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise UserEmailAlreadyExistsError from error

    database_session.refresh(user)
    return user


def get_user_by_id(database_session: Session, user_id: UUID) -> User | None:
    """Return one user by ID, or None when it does not exist."""
    return database_session.get(User, user_id)


def list_users(database_session: Session, *, offset: int = 0, limit: int = 100) -> list[User]:
    """Return a paginated list of users."""
    statement = select(User).order_by(User.created_at).offset(offset).limit(limit)
    return list(database_session.scalars(statement).all())


def update_user(database_session: Session, user: User, user_data: UserUpdate) -> User:
    """Update the fields allowed by the general User update endpoint."""
    if user_data.display_name is not None:
        user.display_name = user_data.display_name

    database_session.commit()
    database_session.refresh(user)
    return user


def delete_user(database_session: Session, user: User) -> None:
    """Permanently remove a user."""
    database_session.delete(user)
    database_session.commit()


def get_user_by_email(database_session: Session, email: str) -> User | None:
    """Return one user by email address, or None when it does not exist."""
    statement = select(User).where(User.email == email)
    return database_session.scalar(statement)


def authenticate_user(database_session: Session, login_data: LoginRequest) -> User | None:
    """Return the user when credentials are valid, otherwise None."""
    user = get_user_by_email(database_session, str(login_data.email).lower())

    if user is None:
        return None

    if not verify_password(login_data.password, user.password_hash):
        return None

    return user
