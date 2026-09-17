from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.billing import Tariff
from app.models.energy import ChargingSession
from app.models.user import User, UserRole
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_auth_authorization import login_headers
from tests.test_charging_session_domain import (
    create_charger,
    create_user_and_headers,
    create_vehicle,
    start_session,
)
from tests.test_energy import create_session_dependencies


@pytest.mark.anyio
async def test_tariff_crud_keeps_only_latest_active(client: AsyncClient) -> None:
    first = await client.post(
        "/api/v1/tariffs",
        json={
            "name": "Standard",
            "price_per_kwh": "0.9200",
            "currency": "brl",
            "valid_from": "2026-08-20T00:00:00Z",
        },
    )
    assert first.status_code == 201
    assert first.json()["currency"] == "BRL"

    second = await client.post(
        "/api/v1/tariffs",
        json={
            "name": "Off peak",
            "price_per_kwh": "0.5000",
            "valid_from": "2026-09-01T00:00:00Z",
        },
    )
    assert second.status_code == 201
    tariffs = (await client.get("/api/v1/tariffs")).json()
    assert [tariff["name"] for tariff in tariffs if tariff["is_active"]] == ["Off peak"]

    invalid = await client.patch(
        f"/api/v1/tariffs/{second.json()['id']}",
        json={"valid_until": "2026-08-01T00:00:00Z"},
    )
    assert invalid.status_code == 422
    missing = await client.get("/api/v1/tariffs/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404


@pytest.mark.anyio
async def test_only_admin_can_change_tariffs(client: AsyncClient, db_session: Session) -> None:
    user = User(
        name="Driver", email="tariff-driver@example.com",
        password_hash=hash_password("secret123"), role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    headers = await login_headers(client, user.email, "secret123")
    tariff = db_session.query(Tariff).first()
    assert tariff is not None
    payload = {
        "name": "Unauthorized", "price_per_kwh": "0.0100",
        "valid_from": "2020-01-01T00:00:00Z",
    }
    assert (await client.post("/api/v1/tariffs", headers=headers, json=payload)).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/tariffs/{tariff.id}", headers=headers,
            json={"price_per_kwh": "0.0100"},
        )
    ).status_code == 403
    client.headers.pop("Authorization")
    assert (await client.post("/api/v1/tariffs", json=payload)).status_code == 401
    assert (
        await client.patch(f"/api/v1/tariffs/{tariff.id}", json={"price_per_kwh": "0.0100"})
    ).status_code == 401
    db_session.refresh(tariff)
    assert tariff.price_per_kwh == Decimal("0.9200")


@pytest.mark.anyio
async def test_database_rejects_two_active_tariffs(
    db_session: Session, client: AsyncClient
) -> None:
    db_session.add(
        Tariff(
            name="Duplicate", price_per_kwh=Decimal("1.0000"), currency="BRL",
            is_active=True, valid_from=datetime(2020, 1, 1, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.anyio
async def test_tariff_switch_respects_validity_and_preserves_session_price(
    client: AsyncClient, db_session: Session
) -> None:
    _, headers = await create_user_and_headers(client, suffix="tariff-switch")
    first_vehicle = await create_vehicle(client, headers, suffix="tariff-switch-a")
    first_charger = await create_charger(client, suffix="tariff-switch-a")
    first = await start_session(client, headers, first_vehicle, first_charger)
    assert first.status_code == 201
    admin_headers = await login_headers(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    future = await client.post(
        "/api/v1/tariffs", headers=admin_headers,
        json={
            "name": "Future", "price_per_kwh": "1.5000",
            "valid_from": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert future.status_code == 201
    second_vehicle = await create_vehicle(client, headers, suffix="tariff-switch-b")
    second_charger = await create_charger(client, suffix="tariff-switch-b")
    assert (await start_session(client, headers, second_vehicle, second_charger)).status_code == 409
    activated = await client.patch(
        f"/api/v1/tariffs/{future.json()['id']}", headers=admin_headers,
        json={"valid_from": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    )
    assert activated.status_code == 200
    second = await start_session(client, headers, second_vehicle, second_charger)
    assert second.status_code == 201
    assert first.json()["tariff_per_kwh"] == "0.9200"
    assert second.json()["tariff_per_kwh"] == "1.5000"
    session = db_session.get(ChargingSession, UUID(first.json()["id"]))
    assert session is not None
    session.energy_consumed_kwh = 10
    db_session.commit()
    stopped = await client.post(f"/api/v1/sessions/{session.id}/stop", headers=headers)
    assert stopped.status_code == 200
    assert stopped.json()["tariff_per_kwh"] == "0.9200"
    assert stopped.json()["total_cost"] == "9.20"


@pytest.mark.anyio
async def test_stopping_session_creates_closed_invoice_and_alert(
    client: AsyncClient, db_session: Session
) -> None:
    user, vehicle, station, charger = await create_session_dependencies(client)
    started = await client.post(
        "/api/v1/sessions/start",
        json={
            "vehicle_id": vehicle["id"],
            "charger_id": charger["id"],
        },
    )
    session = db_session.get(ChargingSession, UUID(started.json()["id"]))
    assert session is not None
    session.energy_consumed_kwh = 25
    db_session.commit()

    stopped = await client.post(f"/api/v1/sessions/{session.id}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["total_cost"] == "23.00"

    invoices = (await client.get("/api/v1/billing/invoices", params={"user_id": user["id"]})).json()
    assert len(invoices) == 1
    assert invoices[0]["status"] == "CLOSED"
    assert invoices[0]["energy_kwh"] == "25.0000"
    assert invoices[0]["subtotal"] == "23.00"
    assert invoices[0]["total"] == "23.00"
    assert invoices[0]["closed_at"] is not None
    assert (await client.get(f"/api/v1/billing/invoices/{invoices[0]['id']}")).status_code == 200

    alerts = (await client.get(
        "/api/v1/alerts", params={"station_id": station["id"], "acknowledged": "false"}
    )).json()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "SESSION_FINISHED"
    assert alerts[0]["severity"] == "INFO"
    acknowledged = await client.patch(f"/api/v1/alerts/{alerts[0]['id']}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged_at"] is not None
    again = await client.patch(f"/api/v1/alerts/{alerts[0]['id']}/acknowledge")
    assert again.json()["acknowledged_at"] == acknowledged.json()["acknowledged_at"]
    assert (await client.get("/api/v1/alerts", params={"acknowledged": "false"})).json() == []
