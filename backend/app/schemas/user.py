from typing import Annotated

from pydantic import BaseModel, Field, SecretStr, StringConstraints, field_validator

from app.models.user import UserRole
from app.schemas.common import Name, ORMResponse

Email = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
Password = Annotated[SecretStr, Field(min_length=8, max_length=128)]


def _normalize_email(value: str | None) -> str:
    if value is None:
        raise ValueError("field cannot be null")
    normalized = value.strip().lower()
    local, separator, domain = normalized.partition("@")
    invalid_domain = "." not in domain or domain.startswith(".") or domain.endswith(".")
    if not separator or not local or invalid_domain:
        raise ValueError("invalid email address")
    return normalized


class UserCreate(BaseModel):
    name: Name
    email: Email
    password: Password
    role: UserRole = UserRole.USER
    is_active: bool = True

    _validate_email = field_validator("email")(_normalize_email)


class UserUpdate(BaseModel):
    name: Name | None = None
    email: Email | None = None
    password: Password | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    _validate_email = field_validator("email")(_normalize_email)

    @field_validator("name", "email", "password", "role", "is_active")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class UserResponse(ORMResponse):
    name: str
    email: str
    role: UserRole
    is_active: bool
