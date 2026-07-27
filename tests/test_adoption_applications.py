from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AdoptionApplicationStatus,
    ApplicationStatusEvent,
    Pet,
    PetStatus,
)
from tests.test_pets import (
    create_shelter,
    pet_payload,
    register_and_login,
)


# Helper function to create an available Pet for testing purposes.
def create_available_pet(
    client: TestClient,
) -> dict[str, Any]:
    _, owner_token = register_and_login(client)
    create_shelter(client, owner_token)

    create_response = client.post(
        "/api/v1/shelter/pets",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=pet_payload(),
    )

    assert create_response.status_code == 201

    pet_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/v1/shelter/pets/{pet_id}/publish",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert publish_response.status_code == 200

    return publish_response.json()


# Helper function to register a new adopter and return their authentication token.
def register_adopter(
    client: TestClient,
) -> str:
    _, token = register_and_login(
        client,
        email="adopter@example.com",
        display_name="Test Adopter",
    )

    return token

# Intent: verify an adopter can create and retrieve a draft application.
# Ensures: draft creation is idempotent and returns the same application.
def test_create_or_read_draft_application(
    client: TestClient,
    database_session: Session,
) -> None:
    pet_data = create_available_pet(client)
    adopter_token = register_adopter(client)

    headers = {"Authorization": f"Bearer {adopter_token}"}

    first_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/application/draft",
        headers=headers,
    )
    second_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/application/draft",
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["id"] == second_response.json()["id"]
    assert first_response.json()["status"] == "draft"

    status_events = list(
        database_session.scalars(
            select(ApplicationStatusEvent).where(
                ApplicationStatusEvent.application_id == first_response.json()["id"]
            )
        ).all()
    )

    assert len(status_events) == 1
    assert status_events[0].to_status == AdoptionApplicationStatus.DRAFT

# Intent: verify an applicant can complete and submit a draft application.
# Ensures: updates persist and submission advances the application status.
def test_applicant_can_update_and_submit_draft(
    client: TestClient,
    database_session: Session,
) -> None:
    pet_data = create_available_pet(client)
    adopter_token = register_adopter(client)

    headers = {"Authorization": f"Bearer {adopter_token}"}

    create_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/application/draft",
        headers=headers,
    )

    assert create_response.status_code == 200

    application_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/applications/{application_id}/draft",
        headers=headers,
        json={
            "contact_phone": "512-555-0100",
            "message": "I can provide a loving home.",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["message"] == ("I can provide a loving home.")

    submit_response = client.post(
        f"/api/v1/applications/{application_id}/submit",
        headers=headers,
        json={
            "contact_phone": "512-555-0100",
            "message": "I can provide a loving home.",
            "consent": True,
        },
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"
    assert submit_response.json()["consent_at"] is not None
    assert submit_response.json()["submitted_at"] is not None

    pet = database_session.scalar(select(Pet).where(Pet.id == pet_data["id"]))

    assert pet is not None
    assert pet.status == PetStatus.AVAILABLE

# Intent: verify submitting an application does not hide the pet from others.
# Ensures: other users can still discover the submitted pet.
def test_submitted_pet_remains_visible_to_other_users(
    client: TestClient,
) -> None:
    pet_data = create_available_pet(client)
    adopter_token = register_adopter(client)

    adopter_headers = {"Authorization": f"Bearer {adopter_token}"}

    create_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/application/draft",
        headers=adopter_headers,
    )

    assert create_response.status_code == 200

    submit_response = client.post(
        f"/api/v1/applications/{create_response.json()['id']}/submit",
        headers=adopter_headers,
        json={
            "contact_phone": "512-555-0100",
            "message": "I would love to adopt Luna.",
            "consent": True,
        },
    )

    assert submit_response.status_code == 200

    anonymous_response = client.get("/api/v1/pets")

    assert anonymous_response.status_code == 200
    assert [pet["id"] for pet in anonymous_response.json()] == [pet_data["id"]]

    _, another_user_token = register_and_login(
        client,
        email="another-adopter@example.com",
        display_name="Another Adopter",
    )

    another_user_response = client.get(
        "/api/v1/pets",
        headers={"Authorization": f"Bearer {another_user_token}"},
    )

    assert another_user_response.status_code == 200
    assert [pet["id"] for pet in another_user_response.json()] == [pet_data["id"]]

# Intent: verify application privacy between users.
# Ensures: a user cannot read another user's application.
def test_user_cannot_read_another_users_application(
    client: TestClient,
) -> None:
    pet_data = create_available_pet(client)
    adopter_token = register_adopter(client)

    create_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/application/draft",
        headers={"Authorization": f"Bearer {adopter_token}"},
    )

    assert create_response.status_code == 200

    application_id = create_response.json()["id"]

    _, another_user_token = register_and_login(
        client,
        email="another-adopter@example.com",
        display_name="Another Adopter",
    )

    response = client.patch(
        f"/api/v1/applications/{application_id}/draft",
        headers={"Authorization": f"Bearer {another_user_token}"},
        json={"message": "Unauthorized update"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found."}

# Intent: verify a submitted application cannot be submitted twice.
# Ensures: duplicate submission is rejected safely.
def test_submitted_application_cannot_be_submitted_again(
    client: TestClient,
) -> None:
    pet_data = create_available_pet(client)
    adopter_token = register_adopter(client)

    headers = {"Authorization": f"Bearer {adopter_token}"}

    create_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/application/draft",
        headers=headers,
    )

    assert create_response.status_code == 200

    application_id = create_response.json()["id"]

    submission_data = {
        "contact_phone": "512-555-0100",
        "message": "I can provide a loving home.",
        "consent": True,
    }

    first_response = client.post(
        f"/api/v1/applications/{application_id}/submit",
        headers=headers,
        json=submission_data,
    )
    second_response = client.post(
        f"/api/v1/applications/{application_id}/submit",
        headers=headers,
        json=submission_data,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "Only draft applications can be submitted."}
