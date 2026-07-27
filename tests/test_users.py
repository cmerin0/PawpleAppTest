from sqlalchemy import select

from app.core.security import decode_access_token, verify_password
from app.models.entities import User


# Helper function to register a new user and log them in
# returning the registration response and access token.
def register_and_login(client):
    registration_response = client.post(
        "/api/v1/users",
        json={
            "email": "test@example.com",
            "password": "test-password",
            "display_name": "Carlos Merino",
        },
    )

    assert registration_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "test-password",
        },
    )

    assert login_response.status_code == 200

    return (registration_response.json(), login_response.json()["access_token"])

# Intent: verify registration creates an account securely.
# Ensures: the user is persisted and the password is stored hashed.
def test_register_user_creates_account_and_hashes_password(client, database_session) -> None:
    response = client.post(
        "/api/v1/users",
        json={
            "email": "test@example.com",
            "password": "test-password",
            "display_name": "Carlos Merino",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["email"] == "test@example.com"
    assert response_data["display_name"] == "Carlos Merino"
    assert response_data["is_platform_admin"] is False

    # verifying that the API does not return credentials or password hashes.
    assert "password" not in response_data
    assert "password_hash" not in response_data

    # verifying that the password is hashed in the database.
    user = database_session.scalar(select(User).where(User.email == "test@example.com"))

    # verifying that the user was created and the password is hashed.
    assert user is not None
    assert user.password_hash != "test-password"
    assert verify_password("test-password", user.password_hash)

# Intent: verify registration enforces unique email addresses.
# Ensures: duplicate email registration is rejected.
def test_register_user_rejects_duplicate_email(client) -> None:
    user_data = {
        "email": "test@example.com",
        "password": "test-password",
        "display_name": "Carlos Merino",
    }

    first_response = client.post("/api/v1/users", json=user_data)
    second_response = client.post("/api/v1/users", json=user_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "An account already exists for this email address."}

# Intent: verify valid credentials can authenticate.
# Ensures: login returns a usable access token.
def test_login_returns_valid_access_token(client) -> None:
    registration_response = client.post(
        "/api/v1/users",
        json={
            "email": "test@example.com",
            "password": "test-password",
            "display_name": "Carlos Merino",
        },
    )

    assert registration_response.status_code == 201

    user_id = registration_response.json()["id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "test-password",
        },
    )

    assert login_response.status_code == 200

    response_data = login_response.json()

    # verifying that the response contains a valid access token and token type.
    assert response_data["token_type"] == "bearer"
    assert isinstance(response_data["access_token"], str)

    token_payload = decode_access_token(response_data["access_token"])

    # verifying that the token payload contains the correct user ID in the "sub" claim.
    assert token_payload["sub"] == user_id

# Intent: verify invalid credentials cannot authenticate.
# Ensures: an incorrect password is rejected.
def test_login_rejects_invalid_password(client) -> None:
    # Invalid credentials must not authenticate an existing user.
    client.post(
        "/api/v1/users",
        json={
            "email": "test@example.com",
            "password": "test-password",
            "display_name": "Carlos Merino",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password."}

# Intent: verify the current-user endpoint requires a token.
# Ensures: unauthenticated access is rejected.
def test_get_current_user_requires_token(client) -> None:

    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate authentication credentials."}

# Intent: verify a valid token resolves to the authenticated account.
# Ensures: the endpoint returns the correct user's data.
def test_get_current_user_returns_authenticated_account(client) -> None:
    # A valid token should return the matching account.
    user_data, token = register_and_login(client)

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["id"] == user_data["id"]
    assert response.json()["email"] == "test@example.com"

# Intent: verify an authenticated user can change their display name.
# Ensures: the updated display name is persisted and returned.
def test_update_current_user_updates_display_name(client) -> None:
    # Authenticated users can update their own profile.
    _, token = register_and_login(client)

    response = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Enrique Navarro"},
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Enrique Navarro"

# Intent: verify deleting the current account invalidates its access.
# Ensures: subsequent authenticated requests using that account are rejected.
def test_delete_current_user_invalidates_access(client) -> None:

    _, token = register_and_login(client)

    delete_response = client.delete(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert delete_response.status_code == 204

    read_response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert read_response.status_code == 401
