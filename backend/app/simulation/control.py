"""Single-process, manually driven simulator control."""

import logging
from datetime import UTC, datetime
from threading import RLock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.energy import EnergyReading, SolarReading
from app.models.prediction import SystemConfiguration
from app.services.energy_allocation import EqualSharePowerResolver
from app.simulation.clock import SimulationClock, SimulationClockState
from app.simulation.energy_data import SimulationEnergyDataProvider
from app.simulation.tick import TickResult, execute_tick

logger = logging.getLogger(__name__)


class SimulationController:
    def __init__(self, clock: SimulationClock | None = None) -> None:
        self.clock = clock or SimulationClock(initial_instant=datetime.now(UTC))
        self.last_tick: datetime | None = None
        self.lock = RLock()

    def start(self, db: Session) -> None:
        with self.lock:
            if self.clock.state is SimulationClockState.RUNNING:
                return
            configuration = db.scalar(select(SystemConfiguration).limit(1))
            if configuration is not None:
                self.clock.simulation_speed = configuration.simulation_speed
            db.rollback()
            self.clock.start()
            logger.info("simulation_started")

    def stop(self) -> None:
        with self.lock:
            if self.clock.state is SimulationClockState.STOPPED:
                return
            self.clock.stop()
            logger.info("simulation_stopped")

    def reset(self, db: Session) -> bool:
        """Reset only while stopped, preserving readings and moving past their timestamps."""
        with self.lock:
            if self.clock.state is SimulationClockState.RUNNING:
                return False
            latest_energy = db.scalar(select(func.max(EnergyReading.timestamp)))
            latest_solar = db.scalar(select(func.max(SolarReading.timestamp)))
            db.rollback()
            latest = max(
                (
                    value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
                    for value in (latest_energy, latest_solar)
                    if value is not None
                ),
                default=None,
            )
            next_instant = datetime.now(UTC)
            if latest is not None:
                next_instant = max(next_instant, latest + self.clock.tick_duration)
            self.clock = SimulationClock(
                initial_instant=next_instant,
                simulation_speed=self.clock.simulation_speed,
                real_tick_interval=self.clock.real_tick_interval,
            )
            self.last_tick = None
            logger.info("simulation_reset", extra={"simulated_at": next_instant.isoformat()})
            return True

    def tick(self, db: Session) -> TickResult | None:
        with self.lock:
            if self.clock.state is SimulationClockState.STOPPED:
                return None
            # Authentication performed a SELECT on this request's session.
            # execute_tick owns its transaction and must enter with a clean session.
            db.rollback()
            try:
                result = execute_tick(
                    db,
                    clock=self.clock,
                    solar_provider=SimulationEnergyDataProvider(),
                    power_resolver=EqualSharePowerResolver(),
                )
            except Exception:
                logger.exception("simulation_control_tick_failed")
                raise
            self.last_tick = result.timestamp
            return result


controller = SimulationController()


async def get_simulation_controller() -> SimulationController:
    return controller
