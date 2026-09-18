from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.billing import Invoice, Tariff
from app.models.energy import ChargingSession, ChargingSessionStatus
from app.models.infrastructure import Charger, ChargerStatus, ChargingStation
from app.models.user import User, UserRole
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_auth_authorization import add_user, login_headers
from tests.test_charging_session_domain import (
    create_charger,
    create_user_and_headers,
    create_vehicle,
    start_session,
)
from tests.test_energy import create_session_dependencies


@pytest.mark.anyio
async def test_alert_list_and_acknowledgement_require_admin(
    client: AsyncClient, db_session: Session
) -> None:
    station = ChargingStation(name="Alert station", grid_limit_kw=20, station_peak_solar_kw=10)
    db_session.add(station)
    db_session.flush()
    alert = Alert(
        station_id=station.id,
        type=AlertType.HIGH_DEMAND,
        severity=AlertSeverity.WARNING,
        title="High demand",
        message="Grid import reached the configured threshold.",
    )
    db_session.add(alert)
    db_session.commit()
    user = add_user(db_session, email="alert-user@example.com")
    user_headers = await login_headers(client, user.email)
    admin_headers = dict(client.headers)
    client.headers.pop("Authorization")
    for method, path in (
        (client.get, "/api/v1/alerts"),
        (client.patch, f"/api/v1/alerts/{alert.id}/acknowledge"),
    ):
        assert (await method(path)).status_code == 401
        assert (await method(path, headers=user_headers)).status_code == 403
    assert (await client.get("/api/v1/alerts", headers=admin_headers)).status_code == 200
    assert (
        await client.patch(f"/api/v1/alerts/{alert.id}/acknowledge", headers=admin_headers)
    ).status_code == 200


@pytest.mark.parametrize(
    ("energy_kwh", "expected_total"),
    [(25, "23.00"), (0.125, "0.12"), (0, "0.00")],
)
@pytest.mark.anyio
async def test_stop_bills_accumulated_energy_once(
    client: AsyncClient, db_session: Session, energy_kwh: float, expected_total: str
) -> None:
    _, headers = await create_user_and_headers(client, suffix=f"billing-{energy_kwh}")
    vehicle = await create_vehicle(client, headers, suffix=f"billing-{energy_kwh}")
    charger = await create_charger(client, suffix=f"billing-{energy_kwh}")
    started = await start_session(client, headers, vehicle, charger)
    session_id = UUID(started.json()["id"])
    session = db_session.get(ChargingSession, session_id)
    assert session is not None
    session.energy_consumed_kwh = energy_kwh
    db_session.commit()

    stopped = await client.post(f"/api/v1/sessions/{session_id}/stop", headers=headers)
    assert stopped.status_code == 200
    assert stopped.json()["total_cost"] == expected_total
    assert stopped.json()["status"] == "COMPLETED"
    assert (await client.get(f"/api/v1/chargers/{charger['id']}")).json()["status"] == "AVAILABLE"
    invoices = list(db_session.scalars(select(Invoice).where(Invoice.session_id == session_id)))
    assert len(invoices) == 1
    assert invoices[0].status.value == "CLOSED"
    assert invoices[0].total == invoices[0].subtotal == Decimal(expected_total)
    assert invoices[0].tariff_per_kwh == Decimal("0.9200")
    assert invoices[0].energy_kwh == Decimal(str(energy_kwh))

    repeated = await client.post(f"/api/v1/sessions/{session_id}/stop", headers=headers)
    assert repeated.status_code == 409
    invoices = list(db_session.scalars(select(Invoice).where(Invoice.session_id == session_id)))
    assert len(invoices) == 1


@pytest.mark.anyio
async def test_invoice_failure_rolls_back_session_charger_and_alert(
    client: AsyncClient, db_session: Session
) -> None:
    _, headers = await create_user_and_headers(client, suffix="invoice-rollback")
    vehicle = await create_vehicle(client, headers, suffix="invoice-rollback")
    charger = await create_charger(client, suffix="invoice-rollback")
    started = await start_session(client, headers, vehicle, charger)
    session_id = UUID(started.json()["id"])
    session = db_session.get(ChargingSession, session_id)
    assert session is not None
    session.energy_consumed_kwh = 25
    db_session.commit()

    def reject_invoice(*_: object) -> None:
        raise IntegrityError("INSERT invoice", {}, Exception("simulated invoice failure"))

    event.listen(Invoice, "before_insert", reject_invoice)
    try:
        with pytest.raises(IntegrityError, match="simulated invoice failure"):
            await client.post(f"/api/v1/sessions/{session_id}/stop", headers=headers)
    finally:
        event.remove(Invoice, "before_insert", reject_invoice)

    db_session.expire_all()
    session = db_session.get(ChargingSession, session_id)
    assert session is not None
    assert session.status == ChargingSessionStatus.CHARGING
    assert session.ended_at is None
    assert session.total_cost == Decimal("0.00")
    stored_charger = db_session.get(Charger, UUID(charger["id"]))
    assert stored_charger is not None
    assert stored_charger.status == ChargerStatus.CHARGING
    assert db_session.scalar(select(Invoice).where(Invoice.session_id == session_id)) is None
    station_alert = db_session.scalar(
        select(Alert).where(Alert.station_id == UUID(charger["station_id"]))
    )
    assert station_alert is None


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
        name="Driver",
        email="tariff-driver@example.com",
        password_hash=hash_password("secret123"),
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    headers = await login_headers(client, user.email, "secret123")
    tariff = db_session.query(Tariff).first()
    assert tariff is not None
    payload = {
        "name": "Unauthorized",
        "price_per_kwh": "0.0100",
        "valid_from": "2020-01-01T00:00:00Z",
    }
    assert (await client.post("/api/v1/tariffs", headers=headers, json=payload)).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/tariffs/{tariff.id}",
            headers=headers,
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
            name="Duplicate",
            price_per_kwh=Decimal("1.0000"),
            currency="BRL",
            is_active=True,
            valid_from=datetime(2020, 1, 1, tzinfo=UTC),
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
        "/api/v1/tariffs",
        headers=admin_headers,
        json={
            "name": "Future",
            "price_per_kwh": "1.5000",
            "valid_from": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert future.status_code == 201
    second_vehicle = await create_vehicle(client, headers, suffix="tariff-switch-b")
    second_charger = await create_charger(client, suffix="tariff-switch-b")
    assert (await start_session(client, headers, second_vehicle, second_charger)).status_code == 409
    activated = await client.patch(
        f"/api/v1/tariffs/{future.json()['id']}",
        headers=admin_headers,
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
    admin_headers = dict(client.headers)
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

    alerts = (
        await client.get(
            "/api/v1/alerts",
            params={"station_id": station["id"], "acknowledged": "false"},
            headers=admin_headers,
        )
    ).json()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "SESSION_FINISHED"
    assert alerts[0]["severity"] == "INFO"
    acknowledged = await client.patch(
        f"/api/v1/alerts/{alerts[0]['id']}/acknowledge", headers=admin_headers
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged_at"] is not None
    again = await client.patch(
        f"/api/v1/alerts/{alerts[0]['id']}/acknowledge", headers=admin_headers
    )
    assert again.json()["acknowledged_at"] == acknowledged.json()["acknowledged_at"]
    assert (
        await client.get("/api/v1/alerts", params={"acknowledged": "false"}, headers=admin_headers)
    ).json() == []
