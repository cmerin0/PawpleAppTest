from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import Shelter, ShelterMember, ShelterMemberRole, User
from app.schemas.shelters import ShelterCreate


class ShelterSlugAlreadyExistsError(Exception):
    """Raised when a Shelter slug is already in use."""


class UserAlreadyBelongsToShelterError(Exception):
    """Raised when a User already belongs to a Shelter."""


# Function to create a new Shelter and its owner membership in the database.
def create_shelter(
    database_session: Session, *, owner: User, shelter_data: ShelterCreate
) -> Shelter:

    if owner.shelter_membership is not None:
        raise UserAlreadyBelongsToShelterError

    shelter = Shelter(
        name=shelter_data.name,
        slug=shelter_data.slug,
        email=str(shelter_data.email).lower(),
        phone=shelter_data.phone,
        city=shelter_data.city,
        state=shelter_data.state,
    )

    owner_membership = ShelterMember(
        shelter=shelter,
        user=owner,
        role=ShelterMemberRole.OWNER,
    )

    database_session.add_all([shelter, owner_membership])

    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise ShelterSlugAlreadyExistsError from error

    database_session.refresh(shelter)
    return shelter


# Function to retrieve a Shelter by its ID from the database session.
def get_shelter_by_id(database_session: Session, shelter_id: UUID) -> Shelter | None:
    return database_session.get(Shelter, shelter_id)


# Function to retrieve a Shelter associated with a specific User ID from the database session.
def get_shelter_for_user(database_session: Session, *, user_id: UUID) -> Shelter | None:
    statement = select(Shelter).join(ShelterMember).where(ShelterMember.user_id == user_id)

    return database_session.scalar(statement)
