from functools import (
    lru_cache,  # Import Python's cache decorator so settings are created only once.
)

from pydantic import Field, SecretStr

# Import the base class used to define typed settings and the helper used to
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Define a settings model whose values can be loaded from environment
    # variables and validated according to their type annotations.

    # Require a string named DATABASE_URL (or database_url) in the environment or .env file;
    # Pydantic reads it into this Python attribute.
    database_url: str
    test_database_url: str | None = None
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # Object-storage connection used for Pet images.
    minio_endpoint_url: str
    minio_access_key: str
    minio_secret_key: SecretStr
    minio_bucket: str
    minio_region: str = "us-east-1"
    minio_use_ssl: bool = False
    max_pet_photo_upload_bytes: int = 5 * 1024 * 1024
    minio_endpoint_url: str
    minio_public_endpoint_url: str

    # Keep URLs short-lived. The limits prevent accidentally creating
    # extremely short or unnecessarily long-lived credentials.
    pet_photo_url_expiration_seconds: int = Field(
        default=900,
        ge=60,
        le=3600,
    )

    # Configure the settings model's environment-file and extra-value behavior.
    model_config = SettingsConfigDict(
        env_file=".env",  # Load additional environment values from the .env file.
        env_file_encoding="utf-8",  # Decode the .env file using UTF-8.
        extra="ignore",  # Ignore any extra values in the environment that are not defined here.
    )


# Cache the function result so every caller receives the same Settings object
# instead of repeatedly reading and validating configuration.
@lru_cache
def get_settings() -> Settings:
    # Construct and return the validated application settings.
    return Settings()  # type: ignore[call-arg]


# Load the cached settings once when this module is imported for convenient use elsewhere
# for example as `settings.database_url`.
settings = get_settings()
