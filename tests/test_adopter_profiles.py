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


# Test to create an adopter profile for the authenticated user,
# ensuring that the profile is created successfully and the response is correct.
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


# Test to ensure that creating an adopter profile requires authentication,
# and returns a 401 Unauthorized error if the user is not authenticated.
def test_create_adopter_profile_requires_authentication(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/adopter-profile",
        json={"phone": "512-555-0100"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate authentication credentials."}


# Test to ensure that creating an adopter profile rejects duplicate profiles for the same user,
# returning a 409 Conflict error if the user already has an adopter profile.
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


# Test to read the current authenticated user's adopter profile,
# ensuring that the correct profile data is returned.
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


# Test to ensure that reading the current authenticated user's adopter profile
# returns a 404 Not Found error if the user does not have an adopter profile.
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


# Test to update the current authenticated user's adopter profile,
# ensuring that the profile is updated successfully and the response is correct.
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
