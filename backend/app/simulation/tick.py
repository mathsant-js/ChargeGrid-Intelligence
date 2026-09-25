"""Persist one deterministic simulator tick using an injected power resolver.

The resolver owns allocation and solar distribution. This service
only checks its safety invariants and records the resulting interval energy.
"""

import logging
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.energy import ChargingSession, ChargingSessionStatus, EnergyReading, SolarReading
from app.models.infrastructure import Charger, ChargingStation
from app.models.prediction import SystemConfiguration
from app.models.vehicle import Vehicle
from app.services.energy_allocation import PowerBreakdown, SessionPowerRequest
from app.services.energy_readings import ABSOLUTE_TOLERANCE, build_energy_reading_data
from app.simulation.clock import SimulationClock, SimulationClockState
from app.simulation.energy_data import EnergyDataProvider

logger = logging.getLogger(__name__)


class PowerResolver(Protocol):
    """Supply one breakdown for each charging session at a station."""

    def resolve(
        self,
        *,
        station_id: UUID,
        grid_limit_kw: float,
        solar_available_kw: float,
        sessions: Sequence[SessionPowerRequest],
    ) -> Mapping[UUID, PowerBreakdown]: ...


@dataclass(frozen=True, slots=True)
class TickResult:
    timestamp: datetime
    stations_processed: int
    energy_readings_created: int
    stations_already_processed: int


def execute_tick(
    db: Session,
    *,
    clock: SimulationClock,
    solar_provider: EnergyDataProvider,
    power_resolver: PowerResolver,
) -> TickResult:
    """Commit all readings and accumulators atomically, then advance the clock.

    A station with a SolarReading at the same timestamp is already complete:
    the previous tick committed atomically. The database unique constraints
    also reject concurrent or external duplicate writes.
    """

    if clock.state is not SimulationClockState.RUNNING:
        raise RuntimeError("simulation clock must be running")
    timestamp = clock.current_instant
    processed = 0
    created = 0
    skipped = 0
    try:
        with db.begin():
            configuration = db.scalar(select(SystemConfiguration).limit(1))
            high_demand_threshold = (
                configuration.high_demand_threshold if configuration is not None else 0.85
            )
            high_solar_threshold = (
                configuration.high_solar_availability_threshold
                if configuration is not None
                else None
            )
            rows = db.execute(
                select(ChargingSession, Charger, Vehicle, ChargingStation)
                .join(Charger, ChargingSession.charger_id == Charger.id)
                .join(Vehicle, ChargingSession.vehicle_id == Vehicle.id)
                .join(ChargingStation, Charger.station_id == ChargingStation.id)
                .where(ChargingSession.status == ChargingSessionStatus.CHARGING)
                .order_by(ChargingStation.id, ChargingSession.id)
            ).all()
            stations: dict[UUID, list[tuple[ChargingSession, Charger, Vehicle]]] = defaultdict(list)
            for charging_session, charger, vehicle, station in rows:
                stations[station.id].append((charging_session, charger, vehicle))

            for station_id, members in stations.items():
                # Serialize same-station ticks on PostgreSQL before checking idempotency.
                locked_station = db.scalar(
                    select(ChargingStation)
                    .where(ChargingStation.id == station_id)
                    .with_for_update()
                )
                if locked_station is None:
                    raise RuntimeError("charging station disappeared during tick")
                existing = db.scalar(
                    select(SolarReading.id).where(
                        SolarReading.station_id == station_id,
                        SolarReading.timestamp == timestamp,
                    )
                )
                if existing is not None:
                    skipped += 1
                    continue

                solar_available = solar_provider.solar_available_kw(
                    timestamp, locked_station.station_peak_solar_kw
                )
                if (
                    not math.isfinite(solar_available)
                    or not 0 <= solar_available <= locked_station.station_peak_solar_kw
                ):
                    raise ValueError("solar provider returned power outside station capacity")
                requests = [
                    SessionPowerRequest(
                        session_id=session.id,
                        requested_power_kw=session.requested_power_kw,
                        charger_max_power_kw=charger.max_power_kw,
                        vehicle_max_charge_power_kw=vehicle.max_charge_power_kw,
                    )
                    for session, charger, vehicle in members
                ]
                powers = power_resolver.resolve(
                    station_id=station_id,
                    grid_limit_kw=locked_station.grid_limit_kw,
                    solar_available_kw=solar_available,
                    sessions=requests,
                )
                if set(powers) != {request.session_id for request in requests}:
                    raise ValueError(
                        "power resolver must return every charging session exactly once"
                    )
                grid_total = sum(power.grid_power_kw for power in powers.values())
                solar_total = sum(power.solar_power_kw for power in powers.values())
                if (
                    not math.isfinite(grid_total)
                    or grid_total > locked_station.grid_limit_kw + ABSOLUTE_TOLERANCE
                ):
                    raise ValueError("grid power exceeds station limit")
                if (
                    not math.isfinite(solar_total)
                    or solar_total > solar_available + ABSOLUTE_TOLERANCE
                ):
                    raise ValueError("solar power exceeds available generation")

                previous_timestamp = timestamp - clock.tick_duration
                previous_station_tick = db.scalar(
                    select(SolarReading.id).where(
                        SolarReading.station_id == station_id,
                        SolarReading.timestamp == previous_timestamp,
                    )
                )
                previous_grid_power = 0.0
                if previous_station_tick is not None:
                    previous_grid_power = (
                        db.scalar(
                            select(func.coalesce(func.sum(EnergyReading.grid_power_kw), 0.0))
                            .join(ChargingSession, EnergyReading.session_id == ChargingSession.id)
                            .join(Charger, ChargingSession.charger_id == Charger.id)
                            .where(
                                Charger.station_id == station_id,
                                EnergyReading.timestamp == previous_timestamp,
                            )
                        )
                        or 0.0
                    )
                previous_solar_available = 0.0
                if previous_station_tick is not None:
                    previous_solar_available = (
                        db.scalar(
                            select(SolarReading.available_power_kw).where(
                                SolarReading.station_id == station_id,
                                SolarReading.timestamp == previous_timestamp,
                            )
                        )
                        or 0.0
                    )
                if (
                    grid_total / locked_station.grid_limit_kw >= high_demand_threshold
                    and previous_grid_power / locked_station.grid_limit_kw
                    < high_demand_threshold
                ):
                    db.add(
                        Alert(
                            station_id=station_id,
                            type=AlertType.HIGH_DEMAND,
                            severity=AlertSeverity.WARNING,
                            title="High grid demand",
                            message=(
                                f"Grid import reached {grid_total:.2f} kW of the "
                                f"{locked_station.grid_limit_kw:.2f} kW station limit."
                            ),
                            created_at=timestamp,
                        )
                    )
                if (
                    high_solar_threshold is not None
                    and locked_station.station_peak_solar_kw > 0
                    and solar_available / locked_station.station_peak_solar_kw
                    >= high_solar_threshold
                    and previous_solar_available / locked_station.station_peak_solar_kw
                    < high_solar_threshold
                ):
                    db.add(
                        Alert(
                            station_id=station_id,
                            type=AlertType.HIGH_SOLAR_AVAILABILITY,
                            severity=AlertSeverity.INFO,
                            title="High solar availability",
                            message=(
                                f"Solar generation reached {solar_available:.2f} kW "
                                f"({solar_available / locked_station.station_peak_solar_kw:.0%} "
                                "of configured station peak)."
                            ),
                            created_at=timestamp,
                        )
                    )

                db.add(
                    SolarReading(
                        station_id=station_id,
                        timestamp=timestamp,
                        available_power_kw=solar_available,
                    )
                )
                for (session, _, _), request in zip(members, requests, strict=True):
                    power = powers[session.id]
                    if power.allocated_power_kw > min(
                        request.charger_max_power_kw, request.vehicle_max_charge_power_kw
                    ):
                        raise ValueError("allocation exceeds charger or vehicle limit")
                    reading = build_energy_reading_data(
                        session_id=session.id,
                        timestamp=timestamp,
                        requested_power_kw=request.requested_power_kw,
                        allocated_power_kw=power.allocated_power_kw,
                        solar_power_kw=power.solar_power_kw,
                        grid_power_kw=power.grid_power_kw,
                        interval=clock.tick_duration,
                    )
                    db.add(EnergyReading(**asdict(reading)))
                    session.allocated_power_kw = reading.allocated_power_kw
                    session.energy_consumed_kwh += reading.interval_energy_kwh
                    session.solar_energy_kwh += reading.solar_energy_kwh
                    session.grid_energy_kwh += reading.grid_energy_kwh
                    created += 1
                processed += 1
        clock.advance()
    except Exception:
        logger.exception("simulation_tick_failed", extra={"tick_timestamp": timestamp.isoformat()})
        raise

    logger.info(
        "simulation_tick_completed",
        extra={
            "tick_timestamp": timestamp.isoformat(),
            "stations_processed": processed,
            "energy_readings_created": created,
            "stations_already_processed": skipped,
        },
    )
    return TickResult(timestamp, processed, created, skipped)
