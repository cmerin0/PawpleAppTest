from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Define a Pydantic model for the login request payload, which includes an email and password.
# The model enforces validation rules such as stripping whitespace and forbidding extra fields.
class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# Define a Pydantic model for the access token response
# which includes the access token string and its type.
class AccessToken(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
