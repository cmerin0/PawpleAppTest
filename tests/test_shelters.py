from sqlalchemy import select

from app.models.entities import Shelter, ShelterMember, ShelterMemberRole


# Helper function to register a new user and log them in
def register_and_login(
    client, *, email: str = "owner@mail.com", display_name: str = "Shelter Owner"
):
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


# Intent: verify shelter creation establishes ownership.
# Ensures: the shelter is persisted and its creator receives owner membership.
def test_create_shelter_creates_owner_membership(client, database_session) -> None:
    user_data, token = register_and_login(client)

    response = client.post(
        "/api/v1/shelters",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Austin Animal Rescue",
            "slug": "austin-animal-rescue",
            "email": "hello@austinrescue.org",
            "phone": "512-555-0100",
            "city": "Austin",
            "state": "tx",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["slug"] == "austin-animal-rescue"
    assert response_data["state"] == "TX"

    shelter = database_session.scalar(select(Shelter).where(Shelter.id == response_data["id"]))

    assert shelter is not None

    membership = database_session.scalar(
        select(ShelterMember).where(
            ShelterMember.shelter_id == shelter.id,
            ShelterMember.user_id == user_data["id"],
        )
    )

    assert membership is not None
    assert membership.role == ShelterMemberRole.OWNER


# Intent: verify shelter creation requires authentication.
# Ensures: anonymous users cannot create shelters.
def test_create_shelter_requires_authentication(client) -> None:
    response = client.post(
        "/api/v1/shelters",
        json={
            "name": "Austin Animal Rescue",
            "slug": "austin-animal-rescue",
            "email": "hello@austinrescue.org",
            "phone": "512-555-0100",
            "city": "Austin",
            "state": "TX",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate authentication credentials."}


# Intent: verify shelter slugs are unique.
# Ensures: creating a shelter with an existing slug is rejected.
def test_create_shelter_rejects_duplicate_slug(
    client,
) -> None:

    _, first_token = register_and_login(client)

    _, second_token = register_and_login(
        client,
        email="second-owner@example.com",
        display_name="Second Shelter Owner",
    )

    shelter_data = {
        "name": "Austin Animal Rescue",
        "slug": "austin-animal-rescue",
        "email": "hello@austinrescue.org",
        "phone": "512-555-0100",
        "city": "Austin",
        "state": "TX",
    }

    first_response = client.post(
        "/api/v1/shelters",
        headers={"Authorization": f"Bearer {first_token}"},
        json=shelter_data,
    )

    second_response = client.post(
        "/api/v1/shelters",
        headers={"Authorization": f"Bearer {second_token}"},
        json=shelter_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "A shelter already exists for this slug."}


# Intent: verify a user cannot own or join multiple shelters through creation.
# Ensures: shelter creation is rejected when membership already exists.
def test_create_shelter_rejects_user_with_existing_membership(client) -> None:
    _, token = register_and_login(client)

    headers = {
        "Authorization": f"Bearer {token}",
    }

    first_response = client.post(
        "/api/v1/shelters",
        headers=headers,
        json={
            "name": "Austin Animal Rescue",
            "slug": "austin-animal-rescue",
            "email": "hello@austinrescue.org",
            "phone": "512-555-0100",
            "city": "Austin",
            "state": "TX",
        },
    )

    second_response = client.post(
        "/api/v1/shelters",
        headers=headers,
        json={
            "name": "Dallas Animal Rescue",
            "slug": "dallas-animal-rescue",
            "email": "hello@dallasrescue.org",
            "phone": "214-555-0100",
            "city": "Dallas",
            "state": "TX",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "A user can belong to only one shelter."}


# Intent: verify a member can retrieve their current shelter.
# Ensures: the endpoint returns the shelter associated with the user.
def test_get_current_users_shelter(client) -> None:
    _, token = register_and_login(client)

    headers = {
        "Authorization": f"Bearer {token}",
    }

    create_response = client.post(
        "/api/v1/shelters",
        headers=headers,
        json={
            "name": "Austin Animal Rescue",
            "slug": "austin-animal-rescue",
            "email": "hello@austinrescue.org",
            "phone": "512-555-0100",
            "city": "Austin",
            "state": "TX",
        },
    )

    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/shelters/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == create_response.json()["id"]
    assert response.json()["slug"] == "austin-animal-rescue"


# Intent: verify current-shelter lookup requires authentication.
# Ensures: anonymous requests are rejected.
def test_get_current_users_shelter_requires_authentication(
    client,
) -> None:
    response = client.get("/api/v1/shelters/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate authentication credentials."}


# Intent: verify current-shelter lookup handles users without membership.
# Ensures: users with no shelter receive HTTP 404.
def test_get_current_users_shelter_returns_404_without_membership(
    client,
) -> None:
    _, token = register_and_login(client)

    response = client.get(
        "/api/v1/shelters/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "The current user does not belong to a shelter."}
