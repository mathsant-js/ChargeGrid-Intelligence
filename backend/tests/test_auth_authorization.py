from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.energy import ChargingSession, ChargingSessionStatus
from app.models.user import User, UserRole
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def add_user(
    db: Session,
    *,
    email: str,
    password: str = "password-123",
    role: UserRole = UserRole.USER,
    active: bool = True,
) -> User:
    user = User(
        name=email.split("@")[0].title(),
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def login_headers(
    client: AsyncClient, email: str, password: str = "password-123"
) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.anyio
async def test_login_valid_invalid_inactive_and_me(
    client: AsyncClient, db_session: Session
) -> None:
    user = add_user(db_session, email="person@example.com")
    add_user(db_session, email="inactive@example.com", active=False)

    valid = await client.post(
        "/api/v1/auth/login",
        json={"email": " PERSON@EXAMPLE.COM ", "password": "password-123"},
    )
    assert valid.status_code == 200
    assert valid.json()["token_type"] == "bearer"
    headers = {"Authorization": f"Bearer {valid.json()['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["id"] == str(user.id)
    assert "password_hash" not in me.json()

    wrong = await client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "wrong-password"},
    )
    missing = await client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "password-123"},
    )
    inactive = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "password-123"},
    )
    assert wrong.status_code == missing.status_code == inactive.status_code == 401
    assert wrong.json() == missing.json() == inactive.json()


@pytest.mark.anyio
async def test_missing_invalid_and_expired_tokens(client: AsyncClient, db_session: Session) -> None:
    user = add_user(db_session, email="token@example.com")
    client.headers.pop("Authorization")
    missing = await client.get("/api/v1/auth/me")
    invalid = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid"}
    )
    expired = create_access_token(user.id, expires_delta=timedelta(seconds=-1))
    expired_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
    )
    for response in (missing, invalid, expired_response):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.anyio
async def test_token_stops_working_when_account_becomes_inactive(
    client: AsyncClient, db_session: Session
) -> None:
    user = add_user(db_session, email="deactivated@example.com")
    headers = await login_headers(client, user.email)
    user.is_active = False
    db_session.commit()

    response = await client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.anyio
async def test_user_admin_boundaries_and_role_protection(
    client: AsyncClient, db_session: Session
) -> None:
    user = add_user(db_session, email="regular@example.com")
    headers = await login_headers(client, user.email)

    assert (await client.get("/api/v1/users", headers=headers)).status_code == 403
    assert (
        await client.post(
            "/api/v1/users",
            headers=headers,
            json={"name": "No", "email": "no@example.com", "password": "password-123"},
        )
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/stations/{uuid4()}", headers=headers, json={"name": "No"}
        )
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/chargers/{uuid4()}", headers=headers, json={"name": "No"}
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/v1/stations", headers=headers, json={"name": "No", "grid_limit_kw": 10}
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/v1/chargers",
            headers=headers,
            json={
                "station_id": str(uuid4()),
                "name": "No",
                "code": "NO-1",
                "max_power_kw": 10,
            },
        )
    ).status_code == 403
    role_change = await client.patch(
        f"/api/v1/users/{user.id}", headers=headers, json={"role": "ADMIN"}
    )
    assert role_change.status_code == 403
    db_session.refresh(user)
    assert user.role == UserRole.USER


@pytest.mark.anyio
async def test_user_can_read_and_update_only_own_profile(
    client: AsyncClient, db_session: Session
) -> None:
    first = add_user(db_session, email="profile-first@example.com")
    second = add_user(db_session, email="profile-second@example.com")
    headers = await login_headers(client, first.email)

    own = await client.get(f"/api/v1/users/{first.id}", headers=headers)
    updated = await client.patch(
        f"/api/v1/users/{first.id}", headers=headers, json={"name": "Updated profile"}
    )
    other_get = await client.get(f"/api/v1/users/{second.id}", headers=headers)
    other_patch = await client.patch(
        f"/api/v1/users/{second.id}", headers=headers, json={"name": "IDOR"}
    )

    assert own.status_code == updated.status_code == 200
    assert updated.json()["name"] == "Updated profile"
    assert other_get.status_code == other_patch.status_code == 404
    assert other_get.json() == other_patch.json() == {"detail": "Resource not found"}


@pytest.mark.anyio
async def test_vehicle_and_session_ownership_and_admin_global_access(
    client: AsyncClient, db_session: Session
) -> None:
    first = add_user(db_session, email="first@example.com")
    second = add_user(db_session, email="second@example.com")
    admin_headers = await login_headers(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    station = (
        await client.post(
            "/api/v1/stations",
            headers=admin_headers,
            json={"name": "Auth Station", "grid_limit_kw": 60},
        )
    ).json()
    charger = (
        await client.post(
            "/api/v1/chargers",
            headers=admin_headers,
            json={
                "station_id": station["id"],
                "name": "Auth Charger",
                "code": "AUTH-1",
                "max_power_kw": 22,
            },
        )
    ).json()
    first_headers = await login_headers(client, first.email)
    own_vehicle_response = await client.post(
        "/api/v1/vehicles",
        headers=first_headers,
        json={
            "name": "First EV",
            "brand": "Brand",
            "model": "One",
            "license_plate": "FIRST-1",
            "max_charge_power_kw": 11,
        },
    )
    assert own_vehicle_response.status_code == 201
    own_vehicle = own_vehicle_response.json()
    assert own_vehicle["user_id"] == str(first.id)
    assert (await client.get("/api/v1/stations", headers=first_headers)).status_code == 200
    assert (
        await client.get(f"/api/v1/stations/{station['id']}", headers=first_headers)
    ).status_code == 200
    assert (await client.get("/api/v1/chargers", headers=first_headers)).status_code == 200
    assert (
        await client.get(f"/api/v1/chargers/{charger['id']}", headers=first_headers)
    ).status_code == 200

    second_headers = await login_headers(client, second.email)
    other_vehicle = (
        await client.post(
            "/api/v1/vehicles",
            headers=second_headers,
            json={
                "name": "Second EV",
                "brand": "Brand",
                "model": "Two",
                "license_plate": "SECOND-2",
                "max_charge_power_kw": 11,
            },
        )
    ).json()
    assert (await client.get("/api/v1/vehicles", headers=first_headers)).json() == [own_vehicle]
    updated = await client.patch(
        f"/api/v1/vehicles/{own_vehicle['id']}",
        headers=first_headers,
        json={"name": "Updated EV"},
    )
    assert updated.status_code == 200
    own_vehicle = updated.json()
    assert (
        await client.get(f"/api/v1/vehicles/{other_vehicle['id']}", headers=first_headers)
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/vehicles/{other_vehicle['id']}", headers=first_headers)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/vehicles/{other_vehicle['id']}",
            headers=first_headers,
            json={"name": "IDOR"},
        )
    ).status_code == 404
    owner_change = await client.patch(
        f"/api/v1/vehicles/{own_vehicle['id']}",
        headers=first_headers,
        json={"user_id": str(second.id)},
    )
    assert owner_change.status_code == 403

    started = await client.post(
        "/api/v1/sessions/start",
        headers=first_headers,
        json={
            "user_id": str(second.id),
            "vehicle_id": own_vehicle["id"],
            "charger_id": charger["id"],
        },
    )
    assert started.status_code == 201
    assert started.json()["user_id"] == str(first.id)

    other_session = ChargingSession(
        user_id=second.id,
        vehicle_id=UUID(other_vehicle["id"]),
        charger_id=UUID(charger["id"]),
        status=ChargingSessionStatus.COMPLETED,
        requested_power_kw=11,
        allocated_power_kw=0,
        tariff_per_kwh=Decimal("0.92"),
    )
    db_session.add(other_session)
    db_session.commit()
    assert (await client.get("/api/v1/sessions", headers=first_headers)).json() == [started.json()]
    assert (
        await client.get(f"/api/v1/sessions/{other_session.id}", headers=first_headers)
    ).status_code == 404

    admin_vehicles = await client.get("/api/v1/vehicles", headers=admin_headers)
    admin_sessions = await client.get("/api/v1/sessions", headers=admin_headers)
    assert {item["id"] for item in admin_vehicles.json()} == {
        own_vehicle["id"],
        other_vehicle["id"],
    }
    assert {item["id"] for item in admin_sessions.json()} == {
        started.json()["id"],
        str(other_session.id),
    }
    users = await client.get("/api/v1/users", headers=admin_headers)
    assert users.status_code == 200
    assert all("password_hash" not in item for item in users.json())
    assert (
        await client.post(
            "/api/v1/vehicles",
            headers=admin_headers,
            json={
                "user_id": str(first.id),
                "name": "Admin EV",
                "brand": "Brand",
                "model": "Admin",
                "license_plate": "ADMIN-1",
                "max_charge_power_kw": 11,
            },
        )
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/vehicles/{own_vehicle['id']}",
            headers=admin_headers,
            json={"name": "Admin mutation"},
        )
    ).status_code == 403
    assert (
        await client.delete(
            f"/api/v1/vehicles/{own_vehicle['id']}", headers=admin_headers
        )
    ).status_code == 403
    assert (
        await client.post(
            f"/api/v1/sessions/{started.json()['id']}/stop", headers=admin_headers
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/v1/sessions/start",
            headers=admin_headers,
            json={
                "vehicle_id": own_vehicle["id"],
                "charger_id": charger["id"],
            },
        )
    ).status_code == 403
    assert db_session.scalar(select(User).where(User.id == first.id)) is not None
