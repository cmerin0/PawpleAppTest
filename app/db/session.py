from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The engine manages PostgreSQL connections for the whole application.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # checks a reused connection before FastAPI uses it.
)

# Each API request will receive one Session from this factory.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,  # prevents SQLAlchemy from sending unfinished changes unexpectedly.
    autocommit=False,  # means changes require an intentional commit().
)


# Provide a database session for each request and ensure it is closed after use.
def get_database_session() -> Generator[Session, None, None]:
    database_session = SessionLocal()
    try:
        # gives the session to endpoint; finally closes it even if error occurs.
        yield database_session
    finally:
        database_session.close()
