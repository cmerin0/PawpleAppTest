from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Pet, PetStatus
from tests.test_pets import create_shelter, pet_payload, register_and_login


def create_available_pet(
    client: TestClient,
) -> tuple[dict[str, Any], str]:
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

    return publish_response.json(), owner_token


def test_authenticated_user_can_dismiss_available_pet(
    client: TestClient,
    database_session: Session,
) -> None:
    pet_data, _ = create_available_pet(client)

    _, adopter_token = register_and_login(
        client,
        email="adopter@example.com",
        display_name="Test Adopter",
    )

    response = client.put(
        f"/api/v1/pets/{pet_data['id']}/dismissal",
        headers={"Authorization": f"Bearer {adopter_token}"},
    )

    assert response.status_code == 204

    pet = database_session.scalar(select(Pet).where(Pet.id == pet_data["id"]))

    assert pet is not None
    assert pet.status == PetStatus.AVAILABLE


def test_repeated_pet_dismissal_is_safe(
    client: TestClient,
) -> None:
    pet_data, _ = create_available_pet(client)

    _, adopter_token = register_and_login(
        client,
        email="adopter@example.com",
        display_name="Test Adopter",
    )

    headers = {"Authorization": f"Bearer {adopter_token}"}

    first_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/dismissal",
        headers=headers,
    )
    second_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/dismissal",
        headers=headers,
    )

    assert first_response.status_code == 204
    assert second_response.status_code == 204


def test_dismissed_pet_is_hidden_only_from_dismissing_user(
    client: TestClient,
) -> None:
    pet_data, _ = create_available_pet(client)

    _, dismissing_user_token = register_and_login(
        client,
        email="adopter@example.com",
        display_name="Dismissing Adopter",
    )

    dismissal_response = client.put(
        f"/api/v1/pets/{pet_data['id']}/dismissal",
        headers={"Authorization": f"Bearer {dismissing_user_token}"},
    )

    assert dismissal_response.status_code == 204

    dismissed_users_list_response = client.get(
        "/api/v1/pets",
        headers={"Authorization": f"Bearer {dismissing_user_token}"},
    )

    dismissed_users_read_response = client.get(
        f"/api/v1/pets/{pet_data['id']}",
        headers={"Authorization": f"Bearer {dismissing_user_token}"},
    )

    anonymous_list_response = client.get("/api/v1/pets")
    anonymous_read_response = client.get(f"/api/v1/pets/{pet_data['id']}")

    assert dismissed_users_list_response.status_code == 200
    assert dismissed_users_list_response.json() == []

    assert dismissed_users_read_response.status_code == 404
    assert dismissed_users_read_response.json() == {"detail": "Pet not found."}

    assert anonymous_list_response.status_code == 200
    assert [pet["id"] for pet in anonymous_list_response.json()] == [pet_data["id"]]

    assert anonymous_read_response.status_code == 200
    assert anonymous_read_response.json()["id"] == pet_data["id"]


def test_draft_pet_cannot_be_dismissed(
    client: TestClient,
) -> None:
    _, owner_token = register_and_login(client)
    create_shelter(client, owner_token)

    create_response = client.post(
        "/api/v1/shelter/pets",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=pet_payload(),
    )

    assert create_response.status_code == 201

    response = client.put(
        f"/api/v1/pets/{create_response.json()['id']}/dismissal",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Pet not found."}


def test_pet_dismissal_requires_authentication(
    client: TestClient,
) -> None:
    pet_data, _ = create_available_pet(client)

    response = client.put(
        f"/api/v1/pets/{pet_data['id']}/dismissal",
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate authentication credentials."}
