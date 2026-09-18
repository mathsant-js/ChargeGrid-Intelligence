from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.billing import Invoice, InvoiceStatus
from app.models.energy import ChargingSession, ChargingSessionStatus, EnergyReading
from app.models.infrastructure import Charger, ChargingStation
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.services.analytics import AnalyticsFilters, dashboard, sustainability


def seed(db: Session) -> tuple[User, User, ChargingStation, ChargingSession, ChargingSession]:
    first = User(
        name="First",
        email="analytics-first@example.com",
        password_hash=hash_password("secret123"),
        role=UserRole.USER,
    )
    second = User(
        name="Second",
        email="analytics-second@example.com",
        password_hash=hash_password("secret123"),
        role=UserRole.USER,
    )
    station = ChargingStation(name="One", grid_limit_kw=60)
    db.add_all([first, second, station])
    db.flush()
    charger_a = Charger(station_id=station.id, name="A", code="A", max_power_kw=22)
    charger_b = Charger(station_id=station.id, name="B", code="B", max_power_kw=22)
    vehicle_a = Vehicle(
        user_id=first.id,
        name="A",
        brand="X",
        model="X",
        license_plate="ANA-1",
        max_charge_power_kw=22,
    )
    vehicle_b = Vehicle(
        user_id=second.id,
        name="B",
        brand="X",
        model="X",
        license_plate="ANA-2",
        max_charge_power_kw=22,
    )
    db.add_all([charger_a, charger_b, vehicle_a, vehicle_b])
    db.flush()
    at = datetime(2026, 9, 1, tzinfo=UTC)
    first_session = ChargingSession(
        user_id=first.id,
        vehicle_id=vehicle_a.id,
        charger_id=charger_a.id,
        status=ChargingSessionStatus.COMPLETED,
        started_at=at,
        ended_at=at + timedelta(hours=1),
        requested_power_kw=10,
        allocated_power_kw=0,
        tariff_per_kwh=Decimal("0.9200"),
    )
    second_session = ChargingSession(
        user_id=second.id,
        vehicle_id=vehicle_b.id,
        charger_id=charger_b.id,
        status=ChargingSessionStatus.COMPLETED,
        started_at=at,
        ended_at=at + timedelta(hours=1),
        requested_power_kw=10,
        allocated_power_kw=0,
        tariff_per_kwh=Decimal("2.0000"),
    )
    db.add_all([first_session, second_session])
    db.flush()
    db.add_all(
        [
            EnergyReading(
                session_id=first_session.id,
                timestamp=at + timedelta(minutes=10),
                requested_power_kw=10,
                allocated_power_kw=10,
                solar_power_kw=4,
                grid_power_kw=6,
                interval_energy_kwh=10,
                solar_energy_kwh=4,
                grid_energy_kwh=6,
            ),
            EnergyReading(
                session_id=first_session.id,
                timestamp=at + timedelta(minutes=20),
                requested_power_kw=10,
                allocated_power_kw=10,
                solar_power_kw=1,
                grid_power_kw=9,
                interval_energy_kwh=10,
                solar_energy_kwh=1,
                grid_energy_kwh=9,
            ),
            EnergyReading(
                session_id=second_session.id,
                timestamp=at + timedelta(minutes=10),
                requested_power_kw=10,
                allocated_power_kw=10,
                solar_power_kw=5,
                grid_power_kw=5,
                interval_energy_kwh=10,
                solar_energy_kwh=5,
                grid_energy_kwh=5,
            ),
            Invoice(
                session_id=first_session.id,
                user_id=first.id,
                energy_kwh=Decimal("20"),
                tariff_per_kwh=Decimal("0.92"),
                subtotal=Decimal("18.40"),
                total=Decimal("18.40"),
                status=InvoiceStatus.CLOSED,
                closed_at=at + timedelta(hours=1),
            ),
            Invoice(
                session_id=second_session.id,
                user_id=second.id,
                energy_kwh=Decimal("10"),
                tariff_per_kwh=Decimal("2"),
                subtotal=Decimal("20"),
                total=Decimal("20"),
                status=InvoiceStatus.CANCELLED,
                closed_at=at + timedelta(hours=1),
            ),
        ]
    )
    db.commit()
    return first, second, station, first_session, second_session


def test_analytics_calculation_and_empty_period(db_session: Session) -> None:
    first, _, station, _, _ = seed(db_session)
    filters = AnalyticsFilters(station_id=station.id, user_id=first.id)
    summary = dashboard(db_session, filters)
    assert (summary.session_count, summary.completed_session_count) == (1, 1)
    assert (summary.energy_consumed_kwh, summary.solar_energy_kwh, summary.grid_energy_kwh) == (
        20,
        5,
        15,
    )
    assert summary.billed_total == Decimal("18.40")
    impact = sustainability(db_session, filters, 0.4)
    assert impact.solar_percentage == 25
    assert impact.avoided_co2_kg == 2
    assert impact.estimated_solar_savings == Decimal("4.60")
    all_users = dashboard(db_session, AnalyticsFilters(station_id=station.id))
    assert all_users.energy_consumed_kwh == 30
    assert all_users.billed_total == Decimal("18.40")
    assert sustainability(
        db_session, AnalyticsFilters(station_id=station.id), 0.4
    ).estimated_solar_savings == Decimal("14.60")
    empty = AnalyticsFilters(date_from=datetime(2026, 10, 1, tzinfo=UTC))
    assert dashboard(db_session, empty).energy_consumed_kwh == 0
    assert dashboard(db_session, empty).billed_total == 0
    assert sustainability(db_session, empty, 0.4).solar_percentage == 0


@pytest.mark.anyio
async def test_analytics_api_scope_filters_and_validation(
    client: AsyncClient, db_session: Session
) -> None:
    first, second, station, _, _ = seed(db_session)
    login = await client.post(
        "/api/v1/auth/login", json={"email": first.email, "password": "secret123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    base = "/api/v1/analytics"
    own = await client.get(f"{base}/dashboard", headers=headers)
    assert own.status_code == 200
    assert own.json()["energy_consumed_kwh"] == 20
    assert own.json()["user_id"] == str(first.id)
    assert (await client.get(f"{base}/sustainability", headers=headers)).json()[
        "solar_percentage"
    ] == 25
    for endpoint in ("dashboard", "sustainability"):
        assert (
            await client.get(
                f"{base}/{endpoint}", headers=headers, params={"user_id": str(second.id)}
            )
        ).status_code == 404
        assert (
            await client.get(f"{base}/{endpoint}", headers={"Authorization": "Bearer invalid"})
        ).status_code == 401
        assert (
            await client.get(
                f"{base}/{endpoint}",
                params={"from": "2026-10-01T00:00:00Z", "to": "2026-09-01T00:00:00Z"},
            )
        ).status_code == 422
        assert (
            await client.get(f"{base}/{endpoint}", params={"from": "2026-09-01T00:00:00"})
        ).status_code == 422
    admin = await client.get(f"{base}/dashboard", params={"station_id": str(station.id)})
    assert admin.json()["energy_consumed_kwh"] == 30
    filtered = await client.get(
        f"{base}/dashboard",
        params={
            "user_id": str(first.id),
            "from": "2026-09-01T00:15:00Z",
            "to": "2026-09-01T00:30:00Z",
        },
    )
    assert filtered.json()["energy_consumed_kwh"] == 10
    assert filtered.json()["billed_total"] == "0.00"
    client.headers.pop("Authorization")
    assert (await client.get(f"{base}/dashboard")).status_code == 401


def test_emission_factor_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRID_EMISSION_FACTOR_KG_PER_KWH", "0.45")
    get_settings.cache_clear()
    assert get_settings().grid_emission_factor_kg_per_kwh == 0.45
    get_settings.cache_clear()
