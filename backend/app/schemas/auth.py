from pydantic import BaseModel, SecretStr, field_validator

from app.schemas.user import Email, _normalize_email


class LoginRequest(BaseModel):
    email: Email
    password: SecretStr

    _validate_email = field_validator("email")(_normalize_email)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
