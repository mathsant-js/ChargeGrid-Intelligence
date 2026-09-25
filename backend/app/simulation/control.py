"""Single-process automatic and manual simulator control."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from threading import RLock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.energy import EnergyReading, SolarReading
from app.models.prediction import SystemConfiguration
from app.services.energy_allocation import EqualSharePowerResolver
from app.simulation.clock import SimulationClock, SimulationClockState
from app.simulation.energy_data import SimulationEnergyDataProvider
from app.simulation.tick import TickResult, execute_tick

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]
WaitFunction = Callable[[float], Awaitable[None]]


class SimulationController:
    """Coordinate one non-overlapping simulation runner in this backend process."""

    def __init__(
        self,
        clock: SimulationClock | None = None,
        *,
        session_factory: SessionFactory = SessionLocal,
        wait: WaitFunction = asyncio.sleep,
    ) -> None:
        self.clock = clock or SimulationClock(
            initial_instant=get_settings().demo_simulation_start_utc or datetime.now(UTC)
        )
        self.last_tick: datetime | None = None
        self.lock = RLock()
        self._session_factory = session_factory
        self._wait = wait
        self._runner_task: asyncio.Task[None] | None = None
        self._runner_guard = asyncio.Lock()

    @property
    def runner_active(self) -> bool:
        task = self._runner_task
        return task is not None and not task.done()

    async def startup(self) -> None:
        """Initialize process-local runner resources for the FastAPI lifecycle."""

        logger.info("simulation_controller_started")

    async def shutdown(self) -> None:
        """Stop the clock and wait until the process-local runner has exited."""

        await self.stop()
        logger.info("simulation_controller_shutdown")

    async def start(self, db: Session) -> None:
        """Idempotently start the clock and its single automatic runner."""

        async with self._runner_guard:
            with self.lock:
                if self.clock.state is SimulationClockState.RUNNING:
                    return
                configuration = db.scalar(select(SystemConfiguration).limit(1))
                if configuration is not None:
                    self.clock.simulation_speed = configuration.simulation_speed
                db.rollback()
                self.clock.start()
                self._runner_task = asyncio.create_task(
                    self._run(), name="chargegrid-simulation-runner"
                )
                logger.info("simulation_started")

    async def stop(self) -> None:
        """Idempotently stop automatic ticks and await runner termination."""

        async with self._runner_guard:
            with self.lock:
                was_running = self.clock.state is SimulationClockState.RUNNING
                self.clock.stop()
                task = self._runner_task
            if task is not None and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            self._runner_task = None
            if was_running:
                logger.info("simulation_stopped")

    async def _run(self) -> None:
        """Wait between ticks and isolate failures so the next interval can recover."""

        logger.info("simulation_runner_started")
        try:
            while self.clock.state is SimulationClockState.RUNNING:
                await self._wait(self.clock.real_tick_interval.total_seconds())
                if self.clock.state is not SimulationClockState.RUNNING:
                    break
                try:
                    with self._session_factory() as db:
                        self.tick(db)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("simulation_runner_tick_failed")
        except asyncio.CancelledError:
            logger.info("simulation_runner_cancelled")
            raise
        finally:
            logger.info("simulation_runner_stopped")

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
        """Execute one manual or automatic tick without allowing overlap."""

        with self.lock:
            if self.clock.state is SimulationClockState.STOPPED:
                return None
            db.rollback()
            try:
                result = execute_tick(
                    db,
                    clock=self.clock,
                    solar_provider=SimulationEnergyDataProvider(),
                    power_resolver=EqualSharePowerResolver(),
                )
            except Exception:
                db.rollback()
                logger.exception("simulation_control_tick_failed")
                raise
            self.last_tick = result.timestamp
            return result


controller = SimulationController()


async def get_simulation_controller() -> SimulationController:
    return controller
