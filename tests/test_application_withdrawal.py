from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Pet, PetStatus
from tests.test_adoption_applications import create_available_pet
from tests.test_pets import register_and_login


def create_submitted_application_for_adopter(
    client: TestClient,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    pet_data = create_available_pet(client)

    _, adopter_token = register_and_login(
        client,
        email="adopter@example.com",
        display_name="Test Adopter",
    )

    headers = {"Authorization": f"Bearer {adopter_token}"}

    draft_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/application/draft",
        headers=headers,
    )

    assert draft_response.status_code == 200

    application_id = draft_response.json()["id"]

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

    return submit_response.json(), adopter_token, pet_data


# Intent: verify an applicant can withdraw their submitted application.
# Ensures: the withdrawal succeeds and changes the application to withdrawn.
def test_applicant_can_withdraw_submitted_application(
    client: TestClient,
    database_session: Session,
) -> None:
    application_data, adopter_token, pet_data = (
        create_submitted_application_for_adopter(client)
    )

    response = client.post(
        f"/api/v1/applications/{application_data['id']}/withdraw",
        headers={"Authorization": f"Bearer {adopter_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"

    pet = database_session.scalar(
        select(Pet).where(Pet.id == pet_data["id"])
    )

    assert pet is not None
    assert pet.status == PetStatus.AVAILABLE


# Intent: verify a withdrawn application can be reopened for editing.
# Ensures: reopening preserves the application and returns it to draft status.
def test_withdrawn_application_reopens_as_same_draft(
    client: TestClient,
) -> None:
    application_data, adopter_token, pet_data = (
        create_submitted_application_for_adopter(client)
    )

    headers = {"Authorization": f"Bearer {adopter_token}"}

    withdrawal_response = client.post(
        f"/api/v1/applications/{application_data['id']}/withdraw",
        headers=headers,
    )

    assert withdrawal_response.status_code == 200

    reopen_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/application/draft",
        headers=headers,
    )

    assert reopen_response.status_code == 200
    assert reopen_response.json()["id"] == application_data["id"]
    assert reopen_response.json()["status"] == "draft"
    assert reopen_response.json()["consent_at"] is None
    assert reopen_response.json()["submitted_at"] is None


# Intent: verify withdrawing an application twice is not permitted.
# Ensures: the second withdrawal is rejected without corrupting state.
def test_application_cannot_be_withdrawn_twice(
    client: TestClient,
) -> None:
    application_data, adopter_token, _ = (
        create_submitted_application_for_adopter(client)
    )

    headers = {"Authorization": f"Bearer {adopter_token}"}

    first_response = client.post(
        f"/api/v1/applications/{application_data['id']}/withdraw",
        headers=headers,
    )
    second_response = client.post(
        f"/api/v1/applications/{application_data['id']}/withdraw",
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "This application cannot be withdrawn."
    }


# Intent: verify users cannot withdraw applications they do not own.
# Ensures: cross-user withdrawal attempts are rejected.
def test_user_cannot_withdraw_another_users_application(
    client: TestClient,
) -> None:
    application_data, _, _ = create_submitted_application_for_adopter(client)

    _, another_user_token = register_and_login(
        client,
        email="another-adopter@example.com",
        display_name="Another Adopter",
    )

    response = client.post(
        f"/api/v1/applications/{application_data['id']}/withdraw",
        headers={"Authorization": f"Bearer {another_user_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found."}
