from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.billing import Invoice, Tariff
from app.models.energy import ChargingSession, ChargingSessionStatus
from app.models.infrastructure import Charger, ChargingStation
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.charging_sessions import start_charging_session
from app.services.errors import DomainConflictError


async def create_user_and_headers(
    client: AsyncClient, *, suffix: str
) -> tuple[dict[str, object], dict[str, str]]:
    email = f"driver-{suffix}@example.com"
    user = (
        await client.post(
            "/api/v1/users",
            json={"name": f"Driver {suffix}", "email": email, "password": "secret123"},
        )
    ).json()
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    )
    return user, {"Authorization": f"Bearer {login.json()['access_token']}"}


async def create_vehicle(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    suffix: str,
    max_power_kw: float = 11,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={
            "name": f"EV {suffix}",
            "brand": "GoodCar",
            "model": "E1",
            "license_plate": f"EV-{suffix}",
            "max_charge_power_kw": max_power_kw,
        },
    )
    assert response.status_code == 201
    return response.json()


async def create_charger(
    client: AsyncClient, *, suffix: str, max_power_kw: float = 22
) -> dict[str, object]:
    station = (
        await client.post(
            "/api/v1/stations",
            json={"name": f"Station {suffix}", "grid_limit_kw": 60},
        )
    ).json()
    response = await client.post(
        "/api/v1/chargers",
        json={
            "station_id": station["id"],
            "name": f"Charger {suffix}",
            "code": f"CH-{suffix}",
            "max_power_kw": max_power_kw,
        },
    )
    assert response.status_code == 201
    return response.json()


async def start_session(
    client: AsyncClient,
    headers: dict[str, str],
    vehicle: dict[str, object],
    charger: dict[str, object],
):
    return await client.post(
        "/api/v1/sessions/start",
        headers=headers,
        json={
            "vehicle_id": vehicle["id"],
            "charger_id": charger["id"],
        },
    )


@pytest.mark.anyio
async def test_valid_start_and_power_limited_by_vehicle(client: AsyncClient) -> None:
    _, headers = await create_user_and_headers(client, suffix="valid")
    vehicle = await create_vehicle(client, headers, suffix="valid", max_power_kw=11)
    charger = await create_charger(client, suffix="valid", max_power_kw=22)

    response = await start_session(client, headers, vehicle, charger)

    assert response.status_code == 201
    assert response.json()["status"] == "CHARGING"
    assert response.json()["requested_power_kw"] == 11
    assert response.json()["tariff_per_kwh"] == "0.9200"


@pytest.mark.anyio
async def test_user_cannot_supply_session_tariff(client: AsyncClient) -> None:
    _, headers = await create_user_and_headers(client, suffix="supplied-tariff")
    vehicle = await create_vehicle(client, headers, suffix="supplied-tariff")
    charger = await create_charger(client, suffix="supplied-tariff")

    response = await client.post(
        "/api/v1/sessions/start",
        headers=headers,
        json={
            "vehicle_id": vehicle["id"],
            "charger_id": charger["id"],
            "tariff_per_kwh": "0.01",
        },
    )

    assert response.status_code == 422
    assert "selected by the backend" in response.text


@pytest.mark.anyio
@pytest.mark.parametrize("tariff_state", ["missing", "inactive", "future", "expired"])
async def test_start_rejects_when_no_active_tariff_is_currently_valid(
    client: AsyncClient, db_session: Session, tariff_state: str
) -> None:
    _, headers = await create_user_and_headers(client, suffix=f"tariff-{tariff_state}")
    vehicle = await create_vehicle(client, headers, suffix=f"tariff-{tariff_state}")
    charger = await create_charger(client, suffix=f"tariff-{tariff_state}")
    tariff = db_session.scalar(select(Tariff))
    assert tariff is not None
    now = datetime.now(UTC)
    if tariff_state == "missing":
        db_session.execute(delete(Tariff))
    elif tariff_state == "inactive":
        tariff.is_active = False
    elif tariff_state == "future":
        tariff.valid_from = now + timedelta(days=1)
    else:
        tariff.valid_until = now - timedelta(days=1)
    db_session.commit()

    response = await start_session(client, headers, vehicle, charger)

    assert response.status_code == 409
    assert response.json()["detail"] == "No active tariff is valid for the session start time"


@pytest.mark.anyio
async def test_session_keeps_original_price_after_active_tariff_changes(
    client: AsyncClient, db_session: Session
) -> None:
    _, headers = await create_user_and_headers(client, suffix="tariff-history")
    vehicle = await create_vehicle(client, headers, suffix="tariff-history")
    charger = await create_charger(client, suffix="tariff-history")
    started = await start_session(client, headers, vehicle, charger)
    assert started.status_code == 201
    session_id = UUID(started.json()["id"])

    original_tariff = db_session.scalar(select(Tariff).where(Tariff.is_active.is_(True)))
    assert original_tariff is not None
    original_tariff.is_active = False
    db_session.add(
        Tariff(
            name="New standard",
            price_per_kwh=Decimal("1.5000"),
            currency="BRL",
            is_active=True,
            valid_from=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    session = db_session.get(ChargingSession, session_id)
    assert session is not None
    session.energy_consumed_kwh = 10
    db_session.commit()

    stopped = await client.post(f"/api/v1/sessions/{session_id}/stop", headers=headers)

    assert stopped.status_code == 200
    assert stopped.json()["tariff_per_kwh"] == "0.9200"
    assert stopped.json()["total_cost"] == "9.20"
    invoice = db_session.scalar(select(Invoice).where(Invoice.session_id == session_id))
    assert invoice is not None
    assert invoice.tariff_per_kwh == Decimal("0.9200")
    assert invoice.total == Decimal("9.20")


def test_inactive_user_cannot_start_session(db_session: Session) -> None:
    user = User(
        name="Inactive",
        email="inactive@example.com",
        password_hash=hash_password("secret123"),
        is_active=False,
    )
    station = ChargingStation(name="Station", grid_limit_kw=60)
    db_session.add_all([user, station])
    db_session.flush()
    vehicle = Vehicle(
        user_id=user.id,
        name="EV",
        brand="GoodCar",
        model="E1",
        license_plate="INACTIVE-1",
        max_charge_power_kw=11,
    )
    charger = Charger(
        station_id=station.id, name="Charger", code="INACTIVE", max_power_kw=22
    )
    db_session.add_all([vehicle, charger])
    db_session.flush()

    with pytest.raises(DomainConflictError, match="User is inactive"):
        start_charging_session(
            db_session,
            user=user,
            vehicle=vehicle,
            charger=charger,
        )


@pytest.mark.anyio
async def test_vehicle_from_another_user_is_hidden(client: AsyncClient) -> None:
    _, owner_headers = await create_user_and_headers(client, suffix="owner")
    _, other_headers = await create_user_and_headers(client, suffix="other")
    vehicle = await create_vehicle(client, owner_headers, suffix="owner")
    charger = await create_charger(client, suffix="ownership")

    response = await start_session(client, other_headers, vehicle, charger)

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found"}


@pytest.mark.anyio
async def test_unavailable_charger_rejects_start(client: AsyncClient) -> None:
    _, headers = await create_user_and_headers(client, suffix="unavailable")
    vehicle = await create_vehicle(client, headers, suffix="unavailable")
    charger = await create_charger(client, suffix="unavailable")
    update = await client.patch(
        f"/api/v1/chargers/{charger['id']}",
        json={"status": "UNAVAILABLE"},
    )
    assert update.status_code == 200

    response = await start_session(client, headers, vehicle, charger)

    assert response.status_code == 409
    assert response.json()["detail"] == "Charger is unavailable"


@pytest.mark.anyio
async def test_vehicle_with_active_session_rejects_second_start(client: AsyncClient) -> None:
    _, headers = await create_user_and_headers(client, suffix="vehicle-active")
    vehicle = await create_vehicle(client, headers, suffix="vehicle-active")
    first_charger = await create_charger(client, suffix="vehicle-first")
    second_charger = await create_charger(client, suffix="vehicle-second")
    assert (await start_session(client, headers, vehicle, first_charger)).status_code == 201

    response = await start_session(client, headers, vehicle, second_charger)

    assert response.status_code == 409
    assert response.json()["detail"] == "Vehicle already has an active session"


@pytest.mark.anyio
async def test_charger_with_active_session_rejects_second_start(client: AsyncClient) -> None:
    _, headers = await create_user_and_headers(client, suffix="charger-active")
    first_vehicle = await create_vehicle(client, headers, suffix="charger-first")
    second_vehicle = await create_vehicle(client, headers, suffix="charger-second")
    charger = await create_charger(client, suffix="charger-active")
    assert (await start_session(client, headers, first_vehicle, charger)).status_code == 201

    response = await start_session(client, headers, second_vehicle, charger)

    assert response.status_code == 409
    assert response.json()["detail"] == "Charger already has an active session"


@pytest.mark.anyio
async def test_requested_power_is_limited_by_charger(client: AsyncClient) -> None:
    _, headers = await create_user_and_headers(client, suffix="charger-limit")
    vehicle = await create_vehicle(client, headers, suffix="charger-limit", max_power_kw=22)
    charger = await create_charger(client, suffix="charger-limit", max_power_kw=7.4)

    response = await start_session(client, headers, vehicle, charger)

    assert response.status_code == 201
    assert response.json()["requested_power_kw"] == 7.4


@pytest.mark.anyio
async def test_valid_stop_is_terminal_and_resets_charger(
    client: AsyncClient, db_session: Session
) -> None:
    _, headers = await create_user_and_headers(client, suffix="stop")
    vehicle = await create_vehicle(client, headers, suffix="stop")
    charger = await create_charger(client, suffix="stop")
    started = await start_session(client, headers, vehicle, charger)
    session = db_session.get(ChargingSession, UUID(started.json()["id"]))
    assert session is not None
    session.allocated_power_kw = 5
    db_session.commit()

    response = await client.post(
        f"/api/v1/sessions/{session.id}/stop", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["allocated_power_kw"] == 0
    assert datetime.fromisoformat(body["ended_at"]).tzinfo == UTC
    charger_response = await client.get(f"/api/v1/chargers/{charger['id']}")
    assert charger_response.json()["status"] == "AVAILABLE"
    second_stop = await client.post(
        f"/api/v1/sessions/{session.id}/stop", headers=headers
    )
    assert second_stop.status_code == 409
    assert "cannot transition" in second_stop.json()["detail"]


@pytest.mark.anyio
async def test_other_user_cannot_access_or_stop_session(client: AsyncClient) -> None:
    _, owner_headers = await create_user_and_headers(client, suffix="session-owner")
    _, other_headers = await create_user_and_headers(client, suffix="session-other")
    vehicle = await create_vehicle(client, owner_headers, suffix="session-owner")
    charger = await create_charger(client, suffix="session-owner")
    started = await start_session(client, owner_headers, vehicle, charger)
    session_id = started.json()["id"]

    get_response = await client.get(f"/api/v1/sessions/{session_id}", headers=other_headers)
    stop_response = await client.post(
        f"/api/v1/sessions/{session_id}/stop", headers=other_headers
    )

    assert get_response.status_code == 404
    assert stop_response.status_code == 404
    assert get_response.json() == stop_response.json() == {"detail": "Resource not found"}


def test_terminal_session_cannot_transition_back_to_charging(db_session: Session) -> None:
    session = ChargingSession(status=ChargingSessionStatus.COMPLETED)
    from app.services.charging_sessions import transition_session

    with pytest.raises(DomainConflictError, match="cannot transition"):
        transition_session(session, ChargingSessionStatus.CHARGING)
