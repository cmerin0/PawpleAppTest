from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Pet, PetStatus, ShelterMember, ShelterMemberRole
from tests.test_pets import register_and_login
from tests.test_shelter_applications import create_submitted_application


# test shelter owner can move application to reviewing 
# Intent: verify a shelter owner can advance an application to reviewing.
# Ensures: the permitted status transition succeeds.
def test_shelter_owner_can_move_application_to_reviewing(
    client: TestClient,
) -> None:
    application_data, owner_token, _ = create_submitted_application(client)

    response = client.patch(
        f"/api/v1/shelter/applications/{application_data['id']}/status",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "status": "reviewing",
            "note": "We are reviewing this application.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "reviewing"


# Intent: verify ordinary shelter staff cannot change application status.
# Ensures: unauthorized status changes are rejected.
def test_shelter_staff_cannot_change_application_status(
    client: TestClient,
    database_session: Session,
) -> None:
    application_data, _, shelter_id = create_submitted_application(client)

    staff_user, staff_token = register_and_login(
        client,
        email="staff@example.com",
        display_name="Shelter Staff",
    )

    database_session.add(
        ShelterMember(
            shelter_id=UUID(shelter_id),
            user_id=UUID(staff_user["id"]),
            role=ShelterMemberRole.STAFF,
        )
    )
    database_session.commit()

    response = client.patch(
        f"/api/v1/shelter/applications/{application_data['id']}/status",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"status": "reviewing"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Shelter owner or manager access is required."
    }


# Intent: verify shelter access is isolated between shelters.
# Ensures: a shelter cannot change another shelter's application.
def test_shelter_cannot_change_another_shelters_application(
    client: TestClient,
) -> None:
    application_data, _, _ = create_submitted_application(client)

    _, second_owner_token = register_and_login(
        client,
        email="second-owner@example.com",
        display_name="Second Shelter Owner",
    )

    second_shelter_response = client.post(
        "/api/v1/shelters",
        headers={"Authorization": f"Bearer {second_owner_token}"},
        json={
            "name": "Dallas Animal Rescue",
            "slug": "dallas-animal-rescue",
            "email": "hello@dallasrescue.org",
            "phone": "214-555-0100",
            "city": "Dallas",
            "state": "TX",
        },
    )

    assert second_shelter_response.status_code == 201

    response = client.patch(
        f"/api/v1/shelter/applications/{application_data['id']}/status",
        headers={"Authorization": f"Bearer {second_owner_token}"},
        json={"status": "reviewing"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found."}


# Intent: verify invalid application status transitions are blocked.
# Ensures: the API rejects transitions outside the allowed workflow.
def test_invalid_status_transition_is_rejected(
    client: TestClient,
) -> None:
    application_data, owner_token, _ = create_submitted_application(client)

    response = client.patch(
        f"/api/v1/shelter/applications/{application_data['id']}/status",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "contacted"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "This application cannot transition to the requested status."
    }


# Intent: verify rejecting an application does not remove the pet from adoption.
# Ensures: the pet remains available after rejection.
def test_rejecting_application_keeps_pet_available(
    client: TestClient,
    database_session: Session,
) -> None:
    application_data, owner_token, _ = create_submitted_application(client)

    response = client.patch(
        f"/api/v1/shelter/applications/{application_data['id']}/status",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "rejected"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    pet = database_session.scalar(
        select(Pet).where(Pet.id == application_data["pet_id"])
    )

    assert pet is not None
    assert pet.status == PetStatus.AVAILABLE
