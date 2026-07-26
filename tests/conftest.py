from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import get_database_session
from app.main import app
from app.models.entities import User

if settings.test_database_url is None:
    raise RuntimeError("TEST_DATABASE_URL must be set before running tests.")


test_engine = create_engine(
    settings.test_database_url,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    """Provide one clean test-database session per test."""
    with test_engine.begin() as connection:
        connection.execute(delete(User))

    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()

        with test_engine.begin() as connection:
            connection.execute(delete(User))


@pytest.fixture
def client(database_session: Session) -> Generator[TestClient, None, None]:
    """Make API requests against the isolated test database."""

    def override_database_session() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_database_session] = override_database_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_database_session, None)
