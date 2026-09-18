from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.billing import Invoice, Tariff
from app.models.energy import ChargingSession
from tests.test_charging_session_domain import (
    create_charger,
    create_user_and_headers,
    create_vehicle,
    start_session,
)


@pytest.mark.anyio
async def test_dashboard_session_flow_and_user_scope(
    client: AsyncClient, db_session: Session
) -> None:
    _, first_headers = await create_user_and_headers(client, suffix="dashboard-a")
    first_vehicle = await create_vehicle(client, first_headers, suffix="dashboard-a")
    first_charger = await create_charger(client, suffix="dashboard-a")
    first = await start_session(client, first_headers, first_vehicle, first_charger)
    assert first.status_code == 201
    first_id = UUID(first.json()["id"])

    _, second_headers = await create_user_and_headers(client, suffix="dashboard-b")
    second_vehicle = await create_vehicle(client, second_headers, suffix="dashboard-b")
    second_charger = await create_charger(client, suffix="dashboard-b")
    second = await start_session(client, second_headers, second_vehicle, second_charger)
    assert second.status_code == 201

    session = db_session.get(ChargingSession, first_id)
    assert session is not None
    session.energy_consumed_kwh = 10
    session.solar_energy_kwh = 4
    session.grid_energy_kwh = 6
    tariff = db_session.query(Tariff).filter_by(is_active=True).one()
    tariff.price_per_kwh = Decimal("2.0000")
    db_session.commit()

    current = await client.get("/api/v1/user/dashboard", headers=first_headers)
    assert current.status_code == 200
    body = current.json()
    assert body["current_session"]["id"] == str(first_id)
    assert body["current_session"]["vehicle_name"] == first_vehicle["name"]
    assert body["current_session"]["charger_name"] == first_charger["name"]
    assert body["current_session"]["solar_percentage"] == 40
    assert body["current_session"]["estimated_cost"] == "9.20"
    assert body["current_session"]["invoice_total"] is None
    assert body["current_session"]["duration_seconds"] >= 0
    assert body["session_history"] == body["invoices"] == []

    stopped = await client.post(f"/api/v1/sessions/{first_id}/stop", headers=first_headers)
    assert stopped.status_code == 200
    invoice = db_session.query(Invoice).filter_by(session_id=first_id).one()
    invoice.total = Decimal("8.75")
    db_session.commit()
    finished = (await client.get("/api/v1/user/dashboard", headers=first_headers)).json()
    assert finished["current_session"] is None
    assert finished["session_history"][0]["invoice_total"] == "8.75"
    assert finished["session_history"][0]["estimated_cost"] is None
    assert finished["invoices"][0]["total"] == "8.75"
    second_view = (await client.get("/api/v1/user/dashboard", headers=second_headers)).json()
    assert second_view["current_session"]["id"] == second.json()["id"]
    assert second_view["session_history"] == second_view["invoices"] == []
    second_stop = await client.post(
        f"/api/v1/sessions/{second.json()['id']}/stop", headers=second_headers
    )
    assert second_stop.status_code == 200
    first_view = (await client.get("/api/v1/user/dashboard", headers=first_headers)).json()
    assert [item["id"] for item in first_view["session_history"]] == [str(first_id)]
    assert [item["id"] for item in first_view["invoices"]] == [str(invoice.id)]


@pytest.mark.anyio
async def test_dashboard_requires_regular_user(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/user/dashboard")).status_code == 403
    assert (
        await client.get("/api/v1/user/dashboard", headers={"Authorization": "Bearer invalid"})
    ).status_code == 401
