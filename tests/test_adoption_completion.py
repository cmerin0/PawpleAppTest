from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Pet, PetStatus
from tests.test_shelter_application_approval import (
    move_application_to_contacted,
)


def create_approved_application(
    client: TestClient,
) -> tuple[dict[str, object], str]:
    application_data, owner_token = move_application_to_contacted(client)

    approval_response = client.post(
        f"/api/v1/shelter/applications/{application_data['id']}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"note": "Approved after the interview."},
    )

    assert approval_response.status_code == 200

    return application_data, owner_token


# Intent: verify completing an approved adoption updates the pet lifecycle.
# Ensures: the adoption completes and the pet is marked adopted.
def test_complete_adoption_marks_pet_as_adopted(
    client: TestClient,
    database_session: Session,
) -> None:
    application_data, owner_token = create_approved_application(client)

    response = client.post(
        f"/api/v1/shelter/applications/{application_data['id']}/complete-adoption",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"note": "Adoption finalized."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    pet = database_session.scalar(select(Pet).where(Pet.id == application_data["pet_id"]))

    assert pet is not None
    assert pet.status == PetStatus.ADOPTED


# Intent: verify an adopted pet remains unavailable to public users.
# Ensures: public discovery does not return the adopted pet.
def test_adopted_pet_remains_hidden_from_public_discovery(
    client: TestClient,
) -> None:
    application_data, owner_token = create_approved_application(client)

    completion_response = client.post(
        f"/api/v1/shelter/applications/{application_data['id']}/complete-adoption",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={},
    )

    assert completion_response.status_code == 200

    list_response = client.get("/api/v1/pets")
    read_response = client.get(f"/api/v1/pets/{application_data['pet_id']}")

    assert list_response.status_code == 200
    assert list_response.json() == []

    assert read_response.status_code == 404
    assert read_response.json() == {"detail": "Pet not found."}


# Intent: verify an already completed adoption cannot be completed again.
# Ensures: duplicate completion attempts are rejected safely.
def test_adoption_cannot_be_completed_twice(
    client: TestClient,
) -> None:
    application_data, owner_token = create_approved_application(client)

    headers = {"Authorization": f"Bearer {owner_token}"}
    endpoint = f"/api/v1/shelter/applications/{application_data['id']}/complete-adoption"

    first_response = client.post(
        endpoint,
        headers=headers,
        json={},
    )
    second_response = client.post(
        endpoint,
        headers=headers,
        json={},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "This pet is not pending adoption."}
