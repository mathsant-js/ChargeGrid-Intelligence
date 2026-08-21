from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.energy import ChargingSession
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
async def test_stopping_session_creates_closed_invoice_and_alert(
    client: AsyncClient, db_session: Session
) -> None:
    user, vehicle, station, charger = await create_session_dependencies(client)
    started = await client.post(
        "/api/v1/sessions/start",
        json={
            "user_id": user["id"],
            "vehicle_id": vehicle["id"],
            "charger_id": charger["id"],
            "tariff_per_kwh": "0.92",
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
