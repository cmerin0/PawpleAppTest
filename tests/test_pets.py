from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import ShelterMember, ShelterMemberRole


# Test the creation of a draft pet listing for a shelter,
# ensuring that only users with the appropriate roles can create pets,
# and that pets are not publicly visible until published.
def register_and_login(
    client: TestClient,
    *,
    email: str = "owner@example.com",
    display_name: str = "Shelter Owner",
) -> tuple[dict[str, Any], str]:
    registration_response = client.post(
        "/api/v1/users",
        json={
            "email": email,
            "password": "test-password",
            "display_name": display_name,
        },
    )

    assert registration_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "test-password",
        },
    )

    assert login_response.status_code == 200

    return (
        registration_response.json(),
        login_response.json()["access_token"],
    )


# Helper function to create a shelter for the authenticated user,
# returning the shelter's details for use in subsequent tests.
def create_shelter(client: TestClient, token: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/shelters",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Austin Animal Rescue",
            "slug": "austin-animal-rescue",
            "email": "hello@austinrescue.org",
            "phone": "512-555-0100",
            "city": "Austin",
            "state": "TX",
        },
    )

    assert response.status_code == 201

    return response.json()


# Helper function to generate a sample payload for creating a pet listing,
# which can be used in tests to create draft pets for a shelter.
def pet_payload() -> dict[str, Any]:
    return {
        "name": "Luna",
        "species": "Dog",
        "breed": "Labrador Retriever",
        "sex": "Female",
        "birth_date": "2023-05-10",
        "size": "Large",
        "description": "Friendly and energetic.",
    }


# Intent: verify shelter staff can create a pet listing.
# Ensures: new listings are persisted initially in draft status.
def test_create_pet_creates_draft(client: TestClient) -> None:
    _, token = register_and_login(client)
    shelter = create_shelter(client, token)

    response = client.post(
        "/api/v1/shelter/pets",
        headers={"Authorization": f"Bearer {token}"},
        json=pet_payload(),
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["name"] == "Luna"
    assert response_data["shelter_id"] == shelter["id"]
    assert response_data["status"] == "draft"
    assert response_data["published_at"] is None


# Intent: verify pet creation is limited to authorized shelter roles.
# Ensures: users without owner or manager privileges cannot create pets.
def test_create_pet_requires_owner_or_manager(
    client: TestClient,
    database_session: Session,
) -> None:
    _, owner_token = register_and_login(client)
    shelter = create_shelter(client, owner_token)

    staff_user, staff_token = register_and_login(
        client,
        email="staff@example.com",
        display_name="Shelter Staff",
    )

    database_session.add(
        ShelterMember(
            shelter_id=UUID(shelter["id"]),
            user_id=UUID(staff_user["id"]),
            role=ShelterMemberRole.STAFF,
        )
    )
    database_session.commit()

    response = client.post(
        "/api/v1/shelter/pets",
        headers={"Authorization": f"Bearer {staff_token}"},
        json=pet_payload(),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Shelter owner or manager access is required."}


# Intent: verify draft listings are private before publication.
# Ensures: public pet discovery excludes draft pets.
def test_draft_pet_is_not_public_until_published(client: TestClient) -> None:
    _, token = register_and_login(client)
    create_shelter(client, token)

    create_response = client.post(
        "/api/v1/shelter/pets",
        headers={"Authorization": f"Bearer {token}"},
        json=pet_payload(),
    )

    assert create_response.status_code == 201

    pet_id = create_response.json()["id"]

    list_drafts_response = client.get("/api/v1/pets")

    assert list_drafts_response.status_code == 200
    assert list_drafts_response.json() == []

    publish_response = client.post(
        f"/api/v1/shelter/pets/{pet_id}/publish",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "available"
    assert publish_response.json()["published_at"] is not None

    list_available_response = client.get("/api/v1/pets")

    assert list_available_response.status_code == 200
    assert [pet["id"] for pet in list_available_response.json()] == [pet_id]

    read_response = client.get(f"/api/v1/pets/{pet_id}")

    assert read_response.status_code == 200
    assert read_response.json()["id"] == pet_id


# Intent: verify published pet listings are immutable through the update endpoint.
# Ensures: attempts to edit a published pet are rejected.
def test_published_pet_cannot_be_updated(client: TestClient) -> None:
    _, token = register_and_login(client)
    create_shelter(client, token)

    create_response = client.post(
        "/api/v1/shelter/pets",
        headers={"Authorization": f"Bearer {token}"},
        json=pet_payload(),
    )

    assert create_response.status_code == 201

    pet_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/v1/shelter/pets/{pet_id}/publish",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert publish_response.status_code == 200

    update_response = client.patch(
        f"/api/v1/shelter/pets/{pet_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Updated Luna"},
    )

    assert update_response.status_code == 409
    assert update_response.json() == {"detail": "Only draft pets can be updated."}


# Intent: verify shelter ownership boundaries apply to pet updates.
# Ensures: one shelter cannot modify another shelter's pet.
def test_shelter_cannot_update_another_shelters_pet(client: TestClient) -> None:
    _, first_token = register_and_login(client)
    create_shelter(client, first_token)

    create_pet_response = client.post(
        "/api/v1/shelter/pets",
        headers={"Authorization": f"Bearer {first_token}"},
        json=pet_payload(),
    )

    assert create_pet_response.status_code == 201

    pet_id = create_pet_response.json()["id"]

    _, second_token = register_and_login(
        client,
        email="second-owner@example.com",
        display_name="Second Shelter Owner",
    )

    second_shelter_response = client.post(
        "/api/v1/shelters",
        headers={"Authorization": f"Bearer {second_token}"},
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
        f"/api/v1/shelter/pets/{pet_id}",
        headers={"Authorization": f"Bearer {second_token}"},
        json={"name": "Unauthorized update"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Pet not found."}
