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


def test_curve_is_the_default_energy_data_provider() -> None:
    settings = Settings(_env_file=None)

    assert settings.energy_data_provider == "curve"


def test_telemetry_replay_provider_configuration_is_accepted() -> None:
    settings = Settings(
        energy_data_provider="telemetry_replay",
        telemetry_replay_path="/tmp/telemetry.csv",
        _env_file=None,
    )

    assert settings.energy_data_provider == "telemetry_replay"
    assert str(settings.telemetry_replay_path) == "/tmp/telemetry.csv"


def test_unknown_energy_data_provider_is_rejected() -> None:
    with pytest.raises(ValidationError, match="energy_data_provider"):
        Settings(energy_data_provider="hardware", _env_file=None)
