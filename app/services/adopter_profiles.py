from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import AdopterProfile, User
from app.schemas.adopter_profiles import (
    AdopterProfileCreate,
    AdopterProfileUpdate,
)


class AdopterProfileAlreadyExistsError(Exception):
    """Raised when a User already has an AdopterProfile."""


class AdopterProfileNotFoundError(Exception):
    """Raised when a User does not have an AdopterProfile."""


# function that creates a new AdopterProfile for the authenticated User.
def create_adopter_profile(
    database_session: Session,
    *,
    user: User,
    profile_data: AdopterProfileCreate,
) -> AdopterProfile:
    profile = AdopterProfile(
        user_id=user.id,
        phone=profile_data.phone,
    )

    database_session.add(profile)

    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise AdopterProfileAlreadyExistsError from error

    database_session.refresh(profile)
    return profile


# function that retrieves the authenticated User's AdopterProfile from the database.
def get_adopter_profile_for_user(
    database_session: Session,
    *,
    user: User,
) -> AdopterProfile:
    statement = select(AdopterProfile).where(AdopterProfile.user_id == user.id)
    profile = database_session.scalar(statement)

    if profile is None:
        raise AdopterProfileNotFoundError

    return profile


# function that updates the authenticated User's AdopterProfile in the database.
def update_adopter_profile(
    database_session: Session,
    *,
    profile: AdopterProfile,
    profile_data: AdopterProfileUpdate,
) -> AdopterProfile:
    if "phone" in profile_data.model_fields_set:
        profile.phone = profile_data.phone

    database_session.commit()
    database_session.refresh(profile)
    return profile
