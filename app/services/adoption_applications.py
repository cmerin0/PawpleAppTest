from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.entities import (
    AdoptionApplication,
    AdoptionApplicationStatus,
    ApplicationStatusEvent,
    Pet,
    PetStatus,
    ShelterMember,
    User,
)
from app.schemas.adoption_applications import (
    AdoptionApplicationDraftUpdate,
    AdoptionApplicationSubmit,
)


class AdoptionApplicationNotFoundError(Exception):
    """Raised when an application is not owned by the requested applicant."""


class AdoptionApplicationStateConflictError(Exception):
    """Raised when an operation is invalid for the application's status."""


class PetUnavailableForApplicationError(Exception):
    """Raised when a Pet is no longer available for an application."""


# get_or_create_draft_application retrieves an existing draft application
# for a Pet and applicant, or creates a new draft application
# if none exists, ensuring the Pet is available.
def get_or_create_draft_application(
    database_session: Session,
    *,
    pet_id: UUID,
    applicant: User,
) -> AdoptionApplication:
    pet = database_session.get(Pet, pet_id)

    if pet is None or pet.status is not PetStatus.AVAILABLE:
        raise PetUnavailableForApplicationError

    statement = select(AdoptionApplication).where(
        AdoptionApplication.pet_id == pet_id,
        AdoptionApplication.applicant_user_id == applicant.id,
    )
    application = database_session.scalar(statement)

    if application is not None:
        if application.status is AdoptionApplicationStatus.DRAFT:
            return application

        raise AdoptionApplicationStateConflictError

    application = AdoptionApplication(
        pet_id=pet.id,
        applicant_user_id=applicant.id,
        status=AdoptionApplicationStatus.DRAFT,
    )
    initial_event = ApplicationStatusEvent(
        application=application,
        from_status=None,
        to_status=AdoptionApplicationStatus.DRAFT,
        changed_by_user_id=applicant.id,
        note="Draft application created.",
    )

    database_session.add_all([application, initial_event])

    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()

        existing_application = database_session.scalar(statement)

        if (
            existing_application is not None
            and existing_application.status is AdoptionApplicationStatus.DRAFT
        ):
            return existing_application

        raise AdoptionApplicationStateConflictError from error

    database_session.refresh(application)
    return application


# get_application_for_applicant retrieves an application by its ID,
# but only if it belongs to the current applicant.
def get_application_for_applicant(
    database_session: Session,
    *,
    application_id: UUID,
    applicant: User,
) -> AdoptionApplication:
    """Return an application only when it belongs to the current applicant."""
    statement = select(AdoptionApplication).where(
        AdoptionApplication.id == application_id,
        AdoptionApplication.applicant_user_id == applicant.id,
    )
    application = database_session.scalar(statement)

    if application is None:
        raise AdoptionApplicationNotFoundError

    return application


# list_applications_for_applicant retrieves all applications for the current applicant,
# ordered by creation date, newest first.
def list_applications_for_applicant(
    database_session: Session,
    *,
    applicant: User,
) -> list[AdoptionApplication]:
    statement = (
        select(AdoptionApplication)
        .where(AdoptionApplication.applicant_user_id == applicant.id)
        .order_by(AdoptionApplication.created_at.desc())
    )

    return list(database_session.scalars(statement).all())


# update_draft_application updates the fields of a draft application,
# ensuring that the application is still in draft status.
def update_draft_application(
    database_session: Session,
    *,
    application: AdoptionApplication,
    application_data: AdoptionApplicationDraftUpdate,
) -> AdoptionApplication:
    if application.status is not AdoptionApplicationStatus.DRAFT:
        raise AdoptionApplicationStateConflictError

    for field_name, value in application_data.model_dump(exclude_unset=True).items():
        setattr(application, field_name, value)

    database_session.commit()
    database_session.refresh(application)

    return application


# submit_application transitions a draft application to submitted,
# recording the submission time and creating a status event.
def submit_application(
    database_session: Session,
    *,
    application: AdoptionApplication,
    applicant: User,
    application_data: AdoptionApplicationSubmit,
) -> AdoptionApplication:
    if application.status is not AdoptionApplicationStatus.DRAFT:
        raise AdoptionApplicationStateConflictError

    pet = database_session.get(Pet, application.pet_id)

    if pet is None or pet.status is not PetStatus.AVAILABLE:
        raise PetUnavailableForApplicationError

    submitted_at = datetime.now(UTC)

    application.contact_phone = application_data.contact_phone
    application.message = application_data.message
    application.consent_at = submitted_at
    application.submitted_at = submitted_at
    application.status = AdoptionApplicationStatus.SUBMITTED

    status_event = ApplicationStatusEvent(
        application_id=application.id,
        from_status=AdoptionApplicationStatus.DRAFT,
        to_status=AdoptionApplicationStatus.SUBMITTED,
        changed_by_user_id=applicant.id,
        note="Application submitted.",
    )

    database_session.add(status_event)
    database_session.commit()
    database_session.refresh(application)

    return application

# list_applications_for_shelter retrieves all non-draft applications 
# for Pets owned by a specific Shelter, ordered by submission date, newest first.
def list_applications_for_shelter(
    database_session: Session,
    *,
    shelter_id: UUID,
    offset: int,
    limit: int,
) -> list[AdoptionApplication]:
    statement = (
        select(AdoptionApplication)
        .join(Pet)
        .options(joinedload(AdoptionApplication.applicant))
        .where(
            Pet.shelter_id == shelter_id,
            AdoptionApplication.status != AdoptionApplicationStatus.DRAFT,
        )
        .order_by(AdoptionApplication.submitted_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(database_session.scalars(statement).all())

# get_application_for_shelter retrieves an application by its ID,
# but only if it belongs to a Pet owned by the specified Shelter.
# This ensures that shelter staff can only access applications for their own shelter's pets.
def get_application_for_shelter(
    database_session: Session,
    *,
    application_id: UUID,
    shelter_id: UUID,
) -> AdoptionApplication:
    statement = (
        select(AdoptionApplication)
        .join(Pet)
        .options(joinedload(AdoptionApplication.applicant))
        .where(
            AdoptionApplication.id == application_id,
            Pet.shelter_id == shelter_id,
        )
    )
    application = database_session.scalar(statement)

    if application is None:
        raise AdoptionApplicationNotFoundError

    return application

# update_application_status_for_shelter updates the status of an adoption application,
# ensuring that the transition is valid based on the current status and the new status.
def update_application_status_for_shelter(
    database_session: Session,
    *,
    application: AdoptionApplication,
    membership: ShelterMember,
    new_status: AdoptionApplicationStatus,
    note: str | None,
) -> AdoptionApplication:
    allowed_transitions = {
        AdoptionApplicationStatus.SUBMITTED: {
            AdoptionApplicationStatus.REVIEWING,
            AdoptionApplicationStatus.REJECTED,
        },
        AdoptionApplicationStatus.REVIEWING: {
            AdoptionApplicationStatus.CONTACTED,
            AdoptionApplicationStatus.REJECTED,
        },
        AdoptionApplicationStatus.CONTACTED: {
            AdoptionApplicationStatus.REJECTED,
        },
    }

    permitted_statuses = allowed_transitions.get(
        application.status,
        set(),
    )

    if new_status not in permitted_statuses:
        raise AdoptionApplicationStateConflictError

    previous_status = application.status
    application.status = new_status

    status_event = ApplicationStatusEvent(
        application_id=application.id,
        from_status=previous_status,
        to_status=new_status,
        changed_by_user_id=membership.user_id,
        note=note,
    )

    database_session.add(status_event)
    database_session.commit()
    database_session.refresh(application)

    return application

# approve application for shelter 
def approve_application_for_shelter(
    database_session: Session,
    *,
    application_id: UUID,
    shelter_id: UUID,
    membership: ShelterMember,
    note: str | None,
) -> AdoptionApplication:
    application_statement = (
        select(AdoptionApplication)
        .join(Pet)
        .where(
            AdoptionApplication.id == application_id,
            Pet.shelter_id == shelter_id,
        )
        .with_for_update(of=AdoptionApplication)
    )
    application = database_session.scalar(application_statement)

    if application is None:
        raise AdoptionApplicationNotFoundError

    pet_statement = (
        select(Pet)
        .where(Pet.id == application.pet_id)
        .with_for_update()
    )
    pet = database_session.scalar(pet_statement)

    if pet is None:
        raise AdoptionApplicationNotFoundError

    if application.status is not AdoptionApplicationStatus.CONTACTED:
        raise AdoptionApplicationStateConflictError

    if pet.status is not PetStatus.AVAILABLE:
        raise PetUnavailableForApplicationError

    previous_status = application.status

    application.status = AdoptionApplicationStatus.APPROVED
    pet.status = PetStatus.PENDING

    status_event = ApplicationStatusEvent(
        application_id=application.id,
        from_status=previous_status,
        to_status=AdoptionApplicationStatus.APPROVED,
        changed_by_user_id=membership.user_id,
        note=note,
    )

    database_session.add(status_event)
    database_session.commit()
    database_session.refresh(application)

    return application