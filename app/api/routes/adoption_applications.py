from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_database_session
from app.schemas.adoption_applications import (
    AdoptionApplicationDraftUpdate,
    AdoptionApplicationRead,
    AdoptionApplicationSubmit,
)
from app.services.adoption_applications import (
    AdoptionApplicationNotFoundError,
    AdoptionApplicationStateConflictError,
    PetUnavailableForApplicationError,
    get_application_for_applicant,
    get_or_create_draft_application,
    list_applications_for_applicant,
    submit_application,
    update_draft_application,
)

applications_router = APIRouter(
    prefix="/applications",
    tags=["adoption applications"],
)

pet_application_router = APIRouter(
    prefix="/pets",
    tags=["adoption applications"],
)

DatabaseSession = Annotated[Session, Depends(get_database_session)]


# create or read a draft application for the authenticated User and a specific Pet.
@pet_application_router.put(
    "/{pet_id}/application/draft",
    response_model=AdoptionApplicationRead,
)
def create_or_read_draft_application(
    pet_id: UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> AdoptionApplicationRead:
    try:
        application = get_or_create_draft_application(
            database_session,
            pet_id=pet_id,
            applicant=current_user,
        )
    except PetUnavailableForApplicationError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found.",
        ) from error
    except AdoptionApplicationStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An application already exists for this pet.",
        ) from error

    return AdoptionApplicationRead.model_validate(application)


# list_current_users_applications retrieves all adoption applications
# for the authenticated User.
@applications_router.get(
    "/me",
    response_model=list[AdoptionApplicationRead],
)
def list_current_users_applications(
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> list[AdoptionApplicationRead]:
    applications = list_applications_for_applicant(
        database_session,
        applicant=current_user,
    )

    return [AdoptionApplicationRead.model_validate(application) for application in applications]


# update_current_users_draft_application updates one draft application
# belonging to the authenticated User.
@applications_router.patch(
    "/{application_id}/draft",
    response_model=AdoptionApplicationRead,
)
def update_current_users_draft_application(
    application_id: UUID,
    application_data: AdoptionApplicationDraftUpdate,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> AdoptionApplicationRead:
    """Update one draft application belonging to the current User."""
    try:
        application = get_application_for_applicant(
            database_session,
            application_id=application_id,
            applicant=current_user,
        )
        updated_application = update_draft_application(
            database_session,
            application=application,
            application_data=application_data,
        )
    except AdoptionApplicationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        ) from error
    except AdoptionApplicationStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft applications can be updated.",
        ) from error

    return AdoptionApplicationRead.model_validate(updated_application)


# submit_current_users_application submits one draft application
# belonging to the authenticated User, without changing the Pet's availability.
@applications_router.post(
    "/{application_id}/submit",
    response_model=AdoptionApplicationRead,
)
def submit_current_users_application(
    application_id: UUID,
    application_data: AdoptionApplicationSubmit,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> AdoptionApplicationRead:
    """Submit one draft application without changing the Pet's availability."""
    try:
        application = get_application_for_applicant(
            database_session,
            application_id=application_id,
            applicant=current_user,
        )
        submitted_application = submit_application(
            database_session,
            application=application,
            applicant=current_user,
            application_data=application_data,
        )
    except AdoptionApplicationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        ) from error
    except AdoptionApplicationStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft applications can be submitted.",
        ) from error
    except PetUnavailableForApplicationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This pet is no longer accepting applications.",
        ) from error

    return AdoptionApplicationRead.model_validate(submitted_application)
