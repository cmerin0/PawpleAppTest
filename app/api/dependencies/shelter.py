from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_database_session
from app.models.entities import ShelterMember, ShelterMemberRole

DatabaseSession = Annotated[Session, Depends(get_database_session)]


# This dependency retrieves the current authenticated user's shelter membership,
# if it exists. If the user does not have a shelter membership,
# it raises an HTTP 403 Forbidden error.
def get_current_shelter_member(
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> ShelterMember:
    """Return the authenticated User's one Shelter membership."""
    statement = select(ShelterMember).where(ShelterMember.user_id == current_user.id)
    membership = database_session.scalar(statement)

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A shelter membership is required.",
        )

    return membership


CurrentShelterMember = Annotated[
    ShelterMember,
    Depends(get_current_shelter_member),
]


# This dependency ensures that the current user has a shelter membership
#  with either an owner or manager role.
def get_current_shelter_manager(
    membership: CurrentShelterMember,
) -> ShelterMember:
    """Require an owner or manager for Pet-listing management."""
    if membership.role not in {
        ShelterMemberRole.OWNER,
        ShelterMemberRole.MANAGER,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shelter owner or manager access is required.",
        )

    return membership


CurrentShelterManager = Annotated[
    ShelterMember,
    Depends(get_current_shelter_manager),
]
