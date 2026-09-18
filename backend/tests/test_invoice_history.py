from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceStatus, Tariff
from tests.test_charging_session_domain import (
    create_charger,
    create_user_and_headers,
    create_vehicle,
    start_session,
)


async def closed_invoice(
    client: AsyncClient, db: Session, *, suffix: str, energy_kwh: float
) -> tuple[dict[str, object], dict[str, str], Invoice]:
    user, headers = await create_user_and_headers(client, suffix=suffix)
    vehicle = await create_vehicle(client, headers, suffix=suffix)
    charger = await create_charger(client, suffix=suffix)
    started = await start_session(client, headers, vehicle, charger)
    assert started.status_code == 201
    from app.models.energy import ChargingSession

    session = db.get(ChargingSession, UUID(started.json()["id"]))
    assert session is not None
    session.energy_consumed_kwh = energy_kwh
    db.commit()
    stopped = await client.post(f"/api/v1/sessions/{session.id}/stop", headers=headers)
    assert stopped.status_code == 200
    invoice = db.query(Invoice).filter_by(session_id=session.id).one()
    return user, headers, invoice


@pytest.mark.anyio
async def test_invoice_history_is_scoped_and_admin_can_filter(
    client: AsyncClient, db_session: Session
) -> None:
    first_user, first_headers, first = await closed_invoice(
        client, db_session, suffix="history-a", energy_kwh=10
    )
    second_user, second_headers, second = await closed_invoice(
        client, db_session, suffix="history-b", energy_kwh=20
    )
    base = "/api/v1/billing/invoices"

    own = await client.get(base, headers=first_headers)
    assert own.status_code == 200
    assert [item["id"] for item in own.json()] == [str(first.id)]
    own_filter = await client.get(
        base, headers=first_headers, params={"user_id": str(first_user["id"])}
    )
    assert own_filter.status_code == 200
    assert (await client.get(f"{base}/{first.id}", headers=first_headers)).status_code == 200
    assert (await client.get(base, headers=second_headers)).json()[0]["id"] == str(second.id)

    for response in (
        await client.get(f"{base}/{second.id}", headers=first_headers),
        await client.get(base, headers=first_headers, params={"user_id": str(second_user["id"])}),
        await client.get(f"{base}/{uuid4()}", headers=first_headers),
    ):
        assert response.status_code == 404
        assert response.json() == {"detail": "Resource not found"}

    all_invoices = await client.get(base)
    assert all_invoices.status_code == 200
    assert {item["id"] for item in all_invoices.json()} == {str(first.id), str(second.id)}
    admin_filter = await client.get(base, params={"user_id": str(second_user["id"])})
    assert [item["id"] for item in admin_filter.json()] == [str(second.id)]
    assert (await client.get(f"{base}/{second.id}")).status_code == 200
    assert (await client.get(base, params={"status": "OPEN"})).json() == []
    assert len((await client.get(base, params={"status": "CLOSED"})).json()) == 2
    combined = await client.get(
        base, params={"user_id": str(first_user["id"]), "status": "CLOSED"}
    )
    assert [item["id"] for item in combined.json()] == [str(first.id)]
    assert (await client.get(base, params={"status": "UNKNOWN"})).status_code == 422

    client.headers.pop("Authorization")
    for path in (base, f"{base}/{first.id}"):
        response = await client.get(path)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        invalid = await client.get(path, headers={"Authorization": "Bearer invalid"})
        assert invalid.status_code == 401


@pytest.mark.anyio
async def test_invoice_order_is_stable_and_tariff_changes_do_not_reprice_history(
    client: AsyncClient, db_session: Session
) -> None:
    user, headers, first = await closed_invoice(
        client, db_session, suffix="stable-a", energy_kwh=10
    )
    _, _, second = await closed_invoice(client, db_session, suffix="stable-b", energy_kwh=20)
    timestamp = datetime(2026, 9, 1, tzinfo=UTC)
    first.created_at = second.created_at = timestamp
    first.status = InvoiceStatus.OPEN
    tariff = db_session.query(Tariff).one()
    tariff.price_per_kwh = Decimal("2.0000")
    db_session.commit()

    base = "/api/v1/billing/invoices"
    expected_order = [str(invoice.id) for invoice in sorted((first, second), key=lambda i: i.id)]
    for _ in range(2):
        response = await client.get(base)
        assert [item["id"] for item in response.json()] == expected_order
    open_filter = await client.get(base, params={"status": "OPEN"})
    assert [item["id"] for item in open_filter.json()] == [str(first.id)]
    assert (await client.get(base, headers=headers, params={"status": "CLOSED"})).json() == []
    detail = (await client.get(f"{base}/{first.id}", headers=headers)).json()
    assert detail["user_id"] == str(user["id"])
    assert detail["energy_kwh"] == "10.0000"
    assert detail["tariff_per_kwh"] == "0.9200"
    assert detail["subtotal"] == detail["total"] == "9.20"
    assert detail["closed_at"] is not None
