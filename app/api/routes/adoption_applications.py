from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.shelter import CurrentShelterManager, CurrentShelterMember
from app.db.session import get_database_session
from app.schemas.adoption_applications import (
    AdoptionApplicationDraftUpdate,
    AdoptionApplicationRead,
    AdoptionApplicationSubmit,
    ShelterApplicationApproval,
    ShelterApplicationRead,
    ShelterApplicationStatusUpdate,
)
from app.services.adoption_applications import (
    AdoptionApplicationNotFoundError,
    AdoptionApplicationStateConflictError,
    PetUnavailableForApplicationError,
    approve_application_for_shelter,
    complete_adoption_for_shelter,
    get_application_for_applicant,
    get_application_for_shelter,
    get_or_create_draft_application,
    list_applications_for_applicant,
    list_applications_for_shelter,
    submit_application,
    update_application_status_for_shelter,
    update_draft_application,
    withdraw_application,
)

applications_router = APIRouter(
    prefix="/applications",
    tags=["adoption applications"],
)

pet_application_router = APIRouter(
    prefix="/pets",
    tags=["adoption applications"],
)

shelter_applications_router = APIRouter(
    prefix="/shelter/applications",
    tags=["shelter applications"],
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


# list_current_shelters_applications retrieves all submitted
# or later applications for the authenticated Shelter.
@shelter_applications_router.get("", response_model=list[ShelterApplicationRead])
def list_current_shelters_applications(
    membership: CurrentShelterMember,
    database_session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ShelterApplicationRead]:
    applications = list_applications_for_shelter(
        database_session,
        shelter_id=membership.shelter_id,
        offset=offset,
        limit=limit,
    )

    return [
        ShelterApplicationRead(
            **AdoptionApplicationRead.model_validate(application).model_dump(),
            applicant_display_name=application.applicant.display_name,
        )
        for application in applications
    ]


# update shelter application status apply a permitted normal
# review transition to one application
@shelter_applications_router.patch(
    "/{application_id}/status",
    response_model=ShelterApplicationRead,
)
def update_shelter_application_status(
    application_id: UUID,
    status_data: ShelterApplicationStatusUpdate,
    membership: CurrentShelterManager,
    database_session: DatabaseSession,
) -> ShelterApplicationRead:
    try:
        application = get_application_for_shelter(
            database_session,
            application_id=application_id,
            shelter_id=membership.shelter_id,
        )
        updated_application = update_application_status_for_shelter(
            database_session,
            application=application,
            membership=membership,
            new_status=status_data.status,
            note=status_data.note,
        )
    except AdoptionApplicationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        ) from error
    except AdoptionApplicationStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application cannot transition to the requested status.",
        ) from error

    return ShelterApplicationRead(
        **AdoptionApplicationRead.model_validate(updated_application).model_dump(),
        applicant_display_name=updated_application.applicant.display_name,
    )


# Approve one contacted application and hide its Pet from discovery.
@shelter_applications_router.post(
    "/{application_id}/approve",
    response_model=ShelterApplicationRead,
)
def approve_shelter_application(
    application_id: UUID,
    approval_data: ShelterApplicationApproval,
    membership: CurrentShelterManager,
    database_session: DatabaseSession,
) -> ShelterApplicationRead:
    try:
        approved_application = approve_application_for_shelter(
            database_session,
            application_id=application_id,
            shelter_id=membership.shelter_id,
            membership=membership,
            note=approval_data.note,
        )
    except AdoptionApplicationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        ) from error
    except AdoptionApplicationStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only contacted applications can be approved.",
        ) from error
    except PetUnavailableForApplicationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This pet is no longer available for approval.",
        ) from error

    return ShelterApplicationRead(
        **AdoptionApplicationRead.model_validate(approved_application).model_dump(),
        applicant_display_name=approved_application.applicant.display_name,
    )


# Withdraw one unapproved application owned by the current User.
@applications_router.post(
    "/{application_id}/withdraw",
    response_model=AdoptionApplicationRead,
)
def withdraw_current_users_application(
    application_id: UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> AdoptionApplicationRead:
    try:
        application = get_application_for_applicant(
            database_session,
            application_id=application_id,
            applicant=current_user,
        )
        withdrawn_application = withdraw_application(
            database_session,
            application=application,
            applicant=current_user,
        )
    except AdoptionApplicationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        ) from error
    except AdoptionApplicationStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application cannot be withdrawn.",
        ) from error

    return AdoptionApplicationRead.model_validate(withdrawn_application)


# Mark the approved application's Pet as adopted.
@shelter_applications_router.post(
    "/{application_id}/complete-adoption",
    response_model=ShelterApplicationRead,
)
def complete_shelter_adoption(
    application_id: UUID,
    approval_data: ShelterApplicationApproval,
    membership: CurrentShelterManager,
    database_session: DatabaseSession,
) -> ShelterApplicationRead:
    try:
        completed_application = complete_adoption_for_shelter(
            database_session,
            application_id=application_id,
            shelter_id=membership.shelter_id,
            membership=membership,
            note=approval_data.note,
        )
    except AdoptionApplicationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        ) from error
    except AdoptionApplicationStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved applications can complete an adoption.",
        ) from error
    except PetUnavailableForApplicationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This pet is not pending adoption.",
        ) from error

    return ShelterApplicationRead(
        **AdoptionApplicationRead.model_validate(completed_application).model_dump(),
        applicant_display_name=completed_application.applicant.display_name,
    )
