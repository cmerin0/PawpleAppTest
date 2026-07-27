from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AdoptionApplicationStatus,
    ApplicationStatusEvent,
    Pet,
    PetStatus,
)
from tests.test_shelter_applications import create_submitted_application


def move_application_to_contacted(
    client: TestClient,
) -> tuple[dict[str, object], str]:
    application_data, owner_token, _ = create_submitted_application(client)

    headers = {"Authorization": f"Bearer {owner_token}"}
    application_id = application_data["id"]

    reviewing_response = client.patch(
        f"/api/v1/shelter/applications/{application_id}/status",
        headers=headers,
        json={"status": "reviewing"},
    )

    assert reviewing_response.status_code == 200

    contacted_response = client.patch(
        f"/api/v1/shelter/applications/{application_id}/status",
        headers=headers,
        json={"status": "contacted"},
    )

    assert contacted_response.status_code == 200

    return application_data, owner_token


def test_approving_contacted_application_moves_pet_to_pending(
    client: TestClient,
    database_session: Session,
) -> None:
    application_data, owner_token = move_application_to_contacted(client)

    response = client.post(
        f"/api/v1/shelter/applications/{application_data['id']}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"note": "Approved after the interview."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    pet = database_session.scalar(
        select(Pet).where(Pet.id == application_data["pet_id"])
    )

    assert pet is not None
    assert pet.status == PetStatus.PENDING

    latest_event = database_session.scalar(
        select(ApplicationStatusEvent)
        .where(
            ApplicationStatusEvent.application_id
            == application_data["id"]
        )
        .order_by(ApplicationStatusEvent.created_at.desc())
    )

    assert latest_event is not None
    assert latest_event.from_status == AdoptionApplicationStatus.CONTACTED
    assert latest_event.to_status == AdoptionApplicationStatus.APPROVED


def test_approved_pet_is_hidden_from_public_discovery(
    client: TestClient,
) -> None:
    application_data, owner_token = move_application_to_contacted(client)

    approval_response = client.post(
        f"/api/v1/shelter/applications/{application_data['id']}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={},
    )

    assert approval_response.status_code == 200

    list_response = client.get("/api/v1/pets")
    read_response = client.get(
        f"/api/v1/pets/{application_data['pet_id']}"
    )

    assert list_response.status_code == 200
    assert list_response.json() == []

    assert read_response.status_code == 404
    assert read_response.json() == {"detail": "Pet not found."}


def test_submitted_application_cannot_be_approved_directly(
    client: TestClient,
) -> None:
    application_data, owner_token, _ = create_submitted_application(client)

    response = client.post(
        f"/api/v1/shelter/applications/{application_data['id']}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Only contacted applications can be approved."
    }