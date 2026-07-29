from typing import Any

from fastapi.testclient import TestClient


# Helper function to register a new user and log them in,
# returning the user data and access token.
def register_and_login(
    client: TestClient,
) -> tuple[dict[str, Any], str]:
    registration_response = client.post(
        "/api/v1/users",
        json={
            "email": "adopter@example.com",
            "password": "test-password",
            "display_name": "Test Adopter",
        },
    )

    assert registration_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "adopter@example.com",
            "password": "test-password",
        },
    )

    assert login_response.status_code == 200

    return (
        registration_response.json(),
        login_response.json()["access_token"],
    )


# Intent: verify an authenticated user can create an adopter profile.
# Ensures: the profile is persisted and returned successfully.
def test_create_adopter_profile(
    client: TestClient,
) -> None:
    user_data, token = register_and_login(client)

    response = client.post(
        "/api/v1/adopter-profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "512-555-0100"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == user_data["id"]
    assert response.json()["phone"] == "512-555-0100"


# Intent: verify profile creation requires authentication.
# Ensures: anonymous profile creation is rejected.
def test_create_adopter_profile_requires_authentication(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/adopter-profile",
        json={"phone": "512-555-0100"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate authentication credentials."}


# Intent: verify a user cannot create more than one adopter profile.
# Ensures: duplicate profile creation is rejected.
def test_create_adopter_profile_rejects_duplicate_profile(
    client: TestClient,
) -> None:
    _, token = register_and_login(client)

    headers = {"Authorization": f"Bearer {token}"}

    first_response = client.post(
        "/api/v1/adopter-profile",
        headers=headers,
        json={"phone": "512-555-0100"},
    )

    second_response = client.post(
        "/api/v1/adopter-profile",
        headers=headers,
        json={"phone": "214-555-0100"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "The current user already has an adopter profile."}


# Intent: verify a user can retrieve their current adopter profile.
# Ensures: the endpoint returns that user's persisted profile.
def test_read_current_users_adopter_profile(
    client: TestClient,
) -> None:
    _, token = register_and_login(client)

    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/v1/adopter-profile",
        headers=headers,
        json={"phone": "512-555-0100"},
    )

    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/adopter-profile/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == create_response.json()["id"]
    assert response.json()["phone"] == "512-555-0100"


# Intent: verify profile lookup reports when no profile exists.
# Ensures: a missing adopter profile returns HTTP 404.
def test_read_adopter_profile_returns_404_when_missing(
    client: TestClient,
) -> None:
    _, token = register_and_login(client)

    response = client.get(
        "/api/v1/adopter-profile/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Adopter profile not found."}


# Intent: verify a user can update their adopter profile.
# Ensures: changed profile fields are persisted and returned.
def test_update_current_users_adopter_profile(
    client: TestClient,
) -> None:
    _, token = register_and_login(client)

    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/v1/adopter-profile",
        headers=headers,
        json={"phone": "512-555-0100"},
    )

    assert create_response.status_code == 201

    response = client.patch(
        "/api/v1/adopter-profile/me",
        headers=headers,
        json={"phone": "214-555-0100"},
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "214-555-0100"
