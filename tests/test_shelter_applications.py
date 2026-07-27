from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import ShelterMember, ShelterMemberRole
from tests.test_pets import (
    create_shelter,
    pet_payload,
    register_and_login,
)


# Helper function to create a submitted adoption application for testing purposes.
def create_submitted_application(
    client: TestClient,
) -> tuple[dict[str, Any], str, str]:
    owner_data, owner_token = register_and_login(client)
    shelter = create_shelter(client, owner_token)

    create_pet_response = client.post(
        "/api/v1/shelter/pets",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=pet_payload(),
    )

    assert create_pet_response.status_code == 201

    pet_id = create_pet_response.json()["id"]

    publish_response = client.post(
        f"/api/v1/shelter/pets/{pet_id}/publish",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert publish_response.status_code == 200

    _, adopter_token = register_and_login(
        client,
        email="adopter@example.com",
        display_name="Test Adopter",
    )

    draft_response = client.put(
        f"/api/v1/pets/{pet_id}/application/draft",
        headers={"Authorization": f"Bearer {adopter_token}"},
    )

    assert draft_response.status_code == 200

    application_id = draft_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/applications/{application_id}/submit",
        headers={"Authorization": f"Bearer {adopter_token}"},
        json={
            "contact_phone": "512-555-0100",
            "message": "I can provide a loving home.",
            "consent": True,
        },
    )

    assert submit_response.status_code == 200

    return submit_response.json(), owner_token, shelter["id"]

# Intent: verify a shelter member can list submitted applications.
# Ensures: the list endpoint returns applications for that shelter.
def test_shelter_member_can_list_submitted_applications(
    client: TestClient,
) -> None:
    application_data, owner_token, _ = create_submitted_application(client)

    response = client.get(
        "/api/v1/shelter/applications",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == application_data["id"]
    assert response.json()[0]["status"] == "submitted"
    assert response.json()[0]["applicant_display_name"] == "Test Adopter"

# Intent: verify shelter staff can list submitted applications.
# Ensures: staff receive the same authorized application listing.
def test_shelter_staff_member_can_list_submitted_applications(
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

    response = client.get(
        "/api/v1/shelter/applications",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert response.status_code == 200
    assert [application["id"] for application in response.json()] == [
        application_data["id"]
    ]

# Intent: verify application listings are isolated by shelter.
# Ensures: a shelter cannot list another shelter's applications.
def test_shelter_cannot_list_another_shelters_applications(
    client: TestClient,
) -> None:
    _, _, _ = create_submitted_application(client)

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

    response = client.get(
        "/api/v1/shelter/applications",
        headers={"Authorization": f"Bearer {second_owner_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []
