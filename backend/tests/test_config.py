import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_JWT_SECRET, Settings


@pytest.mark.parametrize("app_env", ["staging", "production", " STAGING ", "PRODUCTION"])
def test_non_local_environment_rejects_default_jwt_secret(app_env: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be changed"):
        Settings(app_env=app_env, jwt_secret_key=DEFAULT_JWT_SECRET, _env_file=None)


@pytest.mark.parametrize("app_env", ["development", "local", "test"])
def test_local_environment_allows_default_jwt_secret(app_env: str) -> None:
    settings = Settings(app_env=app_env, jwt_secret_key=DEFAULT_JWT_SECRET, _env_file=None)

    assert settings.jwt_secret_key == DEFAULT_JWT_SECRET


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_non_local_environment_accepts_a_non_default_secret(app_env: str) -> None:
    secret = "a-secure-environment-specific-secret-123"

    settings = Settings(app_env=app_env, jwt_secret_key=secret, _env_file=None)

    assert settings.jwt_secret_key == secret
