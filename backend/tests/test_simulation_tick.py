"""One tick persists only supplied safe power, atomically and once."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertType
from app.models.energy import ChargingSession, ChargingSessionStatus, EnergyReading, SolarReading
from app.models.infrastructure import Charger, ChargingStation
from app.models.prediction import SystemConfiguration
from app.models.user import User
from app.models.vehicle import Vehicle
from app.simulation.clock import SimulationClock
from app.simulation.energy_data import SimulationEnergyDataProvider
from app.simulation.tick import PowerBreakdown, SessionPowerRequest, execute_tick

INSTANT = datetime(2026, 9, 16, 12, tzinfo=UTC)


class FixedResolver:
    def __init__(self, powers: dict[UUID, PowerBreakdown]) -> None:
        self.powers = powers
        self.calls: list[UUID] = []

    def resolve(
        self,
        *,
        station_id: UUID,
        grid_limit_kw: float,
        solar_available_kw: float,
        sessions: Sequence[SessionPowerRequest],
    ) -> dict[UUID, PowerBreakdown]:
        self.calls.append(station_id)
        return {request.session_id: self.powers[request.session_id] for request in sessions}


class FixedSolarProvider:
    def __init__(self, value: float) -> None:
        self.value = value

    def solar_available_kw(self, timestamp: datetime, station_peak_solar_kw: float) -> float:
        return self.value


def clock() -> SimulationClock:
    value = SimulationClock(initial_instant=INSTANT)
    value.start()
    return value


def add_session(
    db: Session,
    *,
    station: ChargingStation | None = None,
    status: ChargingSessionStatus = ChargingSessionStatus.CHARGING,
) -> tuple[ChargingStation, ChargingSession]:
    if station is None:
        station = ChargingStation(name="Station", grid_limit_kw=20, station_peak_solar_kw=10)
        db.add(station)
        db.flush()
    user = User(name="Driver", email=f"{uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    vehicle = Vehicle(
        user_id=user.id,
        name="EV",
        brand="Brand",
        model="Model",
        license_plate=str(uuid4())[:8],
        max_charge_power_kw=11,
    )
    charger = Charger(station_id=station.id, name="Charger", code=str(uuid4()), max_power_kw=11)
    db.add_all([vehicle, charger])
    db.flush()
    session = ChargingSession(
        user_id=user.id,
        vehicle_id=vehicle.id,
        charger_id=charger.id,
        status=status,
        requested_power_kw=11,
        allocated_power_kw=0,
        energy_consumed_kwh=0,
        solar_energy_kwh=0,
        grid_energy_kwh=0,
        tariff_per_kwh=Decimal("1"),
        total_cost=Decimal("0"),
    )
    db.add(session)
    db.commit()
    return station, session


def counts(db: Session) -> tuple[int, int]:
    return (
        db.scalar(select(func.count()).select_from(EnergyReading)) or 0,
        db.scalar(select(func.count()).select_from(SolarReading)) or 0,
    )


def high_demand_alerts(db: Session) -> list[Alert]:
    return list(db.scalars(select(Alert).where(Alert.type == AlertType.HIGH_DEMAND)))


def configured_threshold(db: Session, threshold: float) -> None:
    db.add(
        SystemConfiguration(
            simulation_speed=60,
            grid_emission_factor_kg_per_kwh=0.1,
            high_demand_threshold=threshold,
            high_solar_availability_threshold=0.8,
            medium_peak_threshold=0.7,
            high_peak_threshold=0.9,
        )
    )
    db.commit()


def alerts_of_type(db: Session, alert_type: AlertType) -> list[Alert]:
    return list(db.scalars(select(Alert).where(Alert.type == alert_type)))


def test_high_solar_alert_is_configurable_and_deduplicated_by_episode(
    db_session: Session,
) -> None:
    station, session = add_session(db_session)
    configured_threshold(db_session, 0.9)
    configuration = db_session.scalar(select(SystemConfiguration))
    assert configuration is not None
    configuration.high_solar_availability_threshold = 0.8
    db_session.commit()
    resolver = FixedResolver({session.id: PowerBreakdown(7, 7, 0)})
    solar = FixedSolarProvider(8)
    tick_clock = clock()

    execute_tick(db_session, clock=tick_clock, solar_provider=solar, power_resolver=resolver)
    assert len(alerts_of_type(db_session, AlertType.HIGH_SOLAR_AVAILABILITY)) == 1
    db_session.rollback()
    execute_tick(db_session, clock=tick_clock, solar_provider=solar, power_resolver=resolver)
    assert len(alerts_of_type(db_session, AlertType.HIGH_SOLAR_AVAILABILITY)) == 1

    db_session.rollback()
    solar.value = 7
    execute_tick(db_session, clock=tick_clock, solar_provider=solar, power_resolver=resolver)
    assert len(alerts_of_type(db_session, AlertType.HIGH_SOLAR_AVAILABILITY)) == 1
    db_session.rollback()
    solar.value = 8
    execute_tick(db_session, clock=tick_clock, solar_provider=solar, power_resolver=resolver)
    assert len(alerts_of_type(db_session, AlertType.HIGH_SOLAR_AVAILABILITY)) == 2


def test_high_demand_threshold_and_new_episode(db_session: Session) -> None:
    station, session = add_session(db_session)
    session_id = session.id
    configured_threshold(db_session, 0.5)
    resolver = FixedResolver({session_id: PowerBreakdown(10, 0, 10)})
    tick_clock = clock()

    execute_tick(
        db_session,
        clock=tick_clock,
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert len(high_demand_alerts(db_session)) == 1
    assert high_demand_alerts(db_session)[0].station_id == station.id
    assert high_demand_alerts(db_session)[0].severity.value == "WARNING"

    db_session.rollback()
    execute_tick(
        db_session,
        clock=tick_clock,
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert len(high_demand_alerts(db_session)) == 1

    db_session.rollback()
    resolver.powers[session_id] = PowerBreakdown(10, 1, 9)
    execute_tick(
        db_session,
        clock=tick_clock,
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert len(high_demand_alerts(db_session)) == 1

    db_session.rollback()
    resolver.powers[session_id] = PowerBreakdown(9, 1, 8)
    execute_tick(
        db_session,
        clock=tick_clock,
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert len(high_demand_alerts(db_session)) == 1

    db_session.rollback()
    resolver.powers[session_id] = PowerBreakdown(10, 0, 10)
    execute_tick(
        db_session,
        clock=tick_clock,
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert len(high_demand_alerts(db_session)) == 2


def test_high_demand_uses_grid_import_and_default_threshold(db_session: Session) -> None:
    _, session = add_session(db_session)
    session_id = session.id
    tick_clock = clock()
    resolver = FixedResolver({session_id: PowerBreakdown(10, 10, 0)})
    execute_tick(
        db_session,
        clock=tick_clock,
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert high_demand_alerts(db_session) == []
    db_session.rollback()
    resolver.powers[session_id] = PowerBreakdown(11, 0, 11)
    execute_tick(
        db_session,
        clock=tick_clock,
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert high_demand_alerts(db_session) == []


def test_high_demand_alert_rolls_back_with_later_station_failure(db_session: Session) -> None:
    station_a, first = add_session(db_session)
    station_b, second = add_session(db_session)
    configured_threshold(db_session, 0.5)
    ordered = sorted(((station_a.id, first.id), (station_b.id, second.id)))
    resolver = FixedResolver(
        {
            ordered[0][1]: PowerBreakdown(10, 0, 10),
            ordered[1][1]: PowerBreakdown(11, 0, 21),
        }
    )
    tick_clock = clock()
    with pytest.raises(ValueError, match="grid power exceeds station limit"):
        execute_tick(
            db_session,
            clock=tick_clock,
            solar_provider=SimulationEnergyDataProvider(),
            power_resolver=resolver,
        )
    assert high_demand_alerts(db_session) == []
    assert counts(db_session) == (0, 0)
    assert tick_clock.current_instant == INSTANT


def test_empty_and_noncharging_sessions_produce_nothing(db_session: Session) -> None:
    resolver = FixedResolver({})
    first = execute_tick(
        db_session,
        clock=clock(),
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert first.energy_readings_created == 0
    assert counts(db_session) == (0, 0)
    assert high_demand_alerts(db_session) == []
    db_session.rollback()
    for status in (
        ChargingSessionStatus.CREATED,
        ChargingSessionStatus.PAUSED,
        ChargingSessionStatus.COMPLETED,
        ChargingSessionStatus.CANCELLED,
    ):
        _, session = add_session(db_session, status=status)
        assert session.energy_consumed_kwh == 0
    result = execute_tick(
        db_session,
        clock=clock(),
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    assert result.stations_processed == 0
    assert counts(db_session) == (0, 0)
    assert high_demand_alerts(db_session) == []
    assert not resolver.calls


def test_multiple_sessions_stations_and_accumulators(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    station_a, first = add_session(db_session)
    _, second = add_session(db_session, station=station_a)
    _, paused = add_session(db_session, station=station_a, status=ChargingSessionStatus.PAUSED)
    station_b, third = add_session(db_session)
    resolver = FixedResolver(
        {
            first.id: PowerBreakdown(9, 4, 5),
            second.id: PowerBreakdown(7, 3, 4),
            third.id: PowerBreakdown(6, 2, 4),
        }
    )
    tick_clock = clock()
    with caplog.at_level("INFO", logger="app.simulation.tick"):
        result = execute_tick(
            db_session,
            clock=tick_clock,
            solar_provider=SimulationEnergyDataProvider(),
            power_resolver=resolver,
        )
    assert (result.stations_processed, result.energy_readings_created) == (2, 3)
    assert set(resolver.calls) == {station_a.id, station_b.id}
    assert counts(db_session) == (3, 2)
    db_session.refresh(paused)
    assert paused.energy_consumed_kwh == 0
    assert paused.allocated_power_kw == 0
    success = next(
        record for record in caplog.records if record.message == "simulation_tick_completed"
    )
    assert success.energy_readings_created == 3
    assert success.tick_timestamp == INSTANT.isoformat()
    readings = db_session.scalars(select(EnergyReading)).all()
    solar = db_session.scalars(select(SolarReading)).all()
    assert {reading.timestamp.replace(tzinfo=UTC) for reading in [*readings, *solar]} == {INSTANT}
    assert all(reading.available_power_kw == 10 for reading in solar)
    for session in (first, second, third):
        db_session.refresh(session)
        own = next(reading for reading in readings if reading.session_id == session.id)
        assert session.allocated_power_kw == own.allocated_power_kw
        assert session.energy_consumed_kwh == pytest.approx(own.interval_energy_kwh)
        assert session.solar_energy_kwh == pytest.approx(own.solar_energy_kwh)
        assert session.grid_energy_kwh == pytest.approx(own.grid_energy_kwh)
        assert own.interval_energy_kwh == pytest.approx(own.solar_energy_kwh + own.grid_energy_kwh)
    db_session.rollback()
    execute_tick(
        db_session,
        clock=tick_clock,
        solar_provider=SimulationEnergyDataProvider(),
        power_resolver=resolver,
    )
    for session in (first, second, third):
        db_session.refresh(session)
        own_readings = db_session.scalars(
            select(EnergyReading).where(EnergyReading.session_id == session.id)
        ).all()
        assert len(own_readings) == 2
        assert session.energy_consumed_kwh == pytest.approx(
            sum(reading.interval_energy_kwh for reading in own_readings)
        )
        assert session.solar_energy_kwh == pytest.approx(
            sum(reading.solar_energy_kwh for reading in own_readings)
        )
        assert session.grid_energy_kwh == pytest.approx(
            sum(reading.grid_energy_kwh for reading in own_readings)
        )


def test_repeat_same_instant_is_idempotent_and_constraints_reject_duplicates(
    db_session: Session,
) -> None:
    station, session = add_session(db_session)
    resolver = FixedResolver({session.id: PowerBreakdown(9, 4, 5)})
    provider = SimulationEnergyDataProvider()
    execute_tick(db_session, clock=clock(), solar_provider=provider, power_resolver=resolver)
    db_session.rollback()
    repeat = execute_tick(
        db_session, clock=clock(), solar_provider=provider, power_resolver=resolver
    )
    assert repeat.stations_already_processed == 1
    assert counts(db_session) == (1, 1)
    db_session.refresh(session)
    assert session.energy_consumed_kwh == pytest.approx(9 / 60)
    db_session.rollback()
    db_session.add(SolarReading(station_id=station.id, timestamp=INSTANT, available_power_kw=10))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    db_session.add(
        EnergyReading(
            session_id=session.id,
            timestamp=INSTANT,
            requested_power_kw=11,
            allocated_power_kw=9,
            solar_power_kw=4,
            grid_power_kw=5,
            interval_energy_kwh=9 / 60,
            solar_energy_kwh=4 / 60,
            grid_energy_kwh=5 / 60,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_failure_rolls_back_all_stations_and_logs(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    station_a, first = add_session(db_session)
    station_b, second = add_session(db_session)
    ordered = sorted(((station_a.id, first.id), (station_b.id, second.id)))
    resolver = FixedResolver(
        {
            ordered[0][1]: PowerBreakdown(9, 4, 5),
            ordered[1][1]: PowerBreakdown(11, 0, 21),
        }
    )
    tick_clock = clock()
    with pytest.raises(ValueError), caplog.at_level("INFO", logger="app.simulation.tick"):
        execute_tick(
            db_session,
            clock=tick_clock,
            solar_provider=SimulationEnergyDataProvider(),
            power_resolver=resolver,
        )
    assert set(resolver.calls) == {station_a.id, station_b.id}
    assert counts(db_session) == (0, 0)
    assert tick_clock.current_instant == INSTANT
    db_session.refresh(first)
    assert first.energy_consumed_kwh == 0
    assert any(record.message == "simulation_tick_failed" for record in caplog.records)
