"""Automatic simulation runner coordination without wall-clock sleeps."""

import asyncio
from threading import Event, Lock, Thread

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.energy import ChargingSession, EnergyReading
from app.models.infrastructure import ChargingStation
from app.simulation.clock import SimulationClock, SimulationClockState
from app.simulation.control import SimulationController
from app.simulation.tick import TickResult
from tests.test_simulation_api import INSTANT, seed_charging_session


class ControlledWait:
    """Expose runner intervals as deterministic test synchronization points."""

    def __init__(self) -> None:
        self.entered: asyncio.Queue[float] = asyncio.Queue()
        self.releases: asyncio.Queue[None] = asyncio.Queue()

    async def __call__(self, seconds: float) -> None:
        await self.entered.put(seconds)
        await self.releases.get()

    async def complete_interval(self) -> float:
        seconds = await self.entered.get()
        await self.releases.put(None)
        return seconds

    async def wait_for_next_interval(self) -> float:
        return await self.entered.get()


def make_controller(
    test_engine: Engine, wait: ControlledWait
) -> tuple[SimulationController, sessionmaker[Session]]:
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    control = SimulationController(
        SimulationClock(initial_instant=INSTANT), session_factory=factory, wait=wait
    )
    return control, factory


@pytest.mark.anyio
async def test_runner_ticks_while_running_uses_fresh_session_and_stops(
    test_engine: Engine, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    wait = ControlledWait()
    control, _ = make_controller(test_engine, wait)
    runner_sessions: list[Session] = []

    def fake_tick(db: Session, **_: object) -> TickResult:
        runner_sessions.append(db)
        timestamp = control.clock.current_instant
        control.clock.advance()
        return TickResult(timestamp, 0, 0, 0)

    monkeypatch.setattr("app.simulation.control.execute_tick", fake_tick)
    await control.start(db_session)
    assert await wait.complete_interval() == 1
    await wait.wait_for_next_interval()
    assert control.clock.current_instant > INSTANT
    assert runner_sessions and runner_sessions[0] is not db_session

    await control.stop()
    stopped_at = control.clock.current_instant
    assert control.clock.state is SimulationClockState.STOPPED
    assert not control.runner_active
    await asyncio.sleep(0)
    assert control.clock.current_instant == stopped_at


@pytest.mark.anyio
async def test_stopped_controller_has_no_ticks_and_repeated_start_has_one_runner(
    test_engine: Engine, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    wait = ControlledWait()
    control, _ = make_controller(test_engine, wait)
    calls = 0

    def fake_tick(db: Session, **_: object) -> TickResult:
        nonlocal calls
        calls += 1
        timestamp = control.clock.current_instant
        control.clock.advance()
        return TickResult(timestamp, 0, 0, 0)

    monkeypatch.setattr("app.simulation.control.execute_tick", fake_tick)
    await asyncio.sleep(0)
    assert calls == 0
    await control.start(db_session)
    first_task = control._runner_task
    await control.start(db_session)
    assert control._runner_task is first_task
    await wait.complete_interval()
    await wait.wait_for_next_interval()
    assert calls == 1
    await control.stop()
    await control.stop()


@pytest.mark.anyio
async def test_runner_recovers_after_isolated_tick_failure(
    test_engine: Engine,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wait = ControlledWait()
    control, _ = make_controller(test_engine, wait)
    attempts = 0

    def flaky_tick(db: Session, **_: object) -> TickResult:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("isolated failure")
        timestamp = control.clock.current_instant
        control.clock.advance()
        return TickResult(timestamp, 0, 0, 0)

    monkeypatch.setattr("app.simulation.control.execute_tick", flaky_tick)
    with caplog.at_level("ERROR"):
        await control.start(db_session)
        await wait.complete_interval()
        await wait.wait_for_next_interval()
        assert control.clock.current_instant == INSTANT
        await wait.releases.put(None)
        await wait.wait_for_next_interval()
    assert attempts == 2
    assert control.clock.current_instant > INSTANT
    assert any(record.message == "simulation_runner_tick_failed" for record in caplog.records)
    await control.shutdown()


@pytest.mark.anyio
async def test_shutdown_cancels_waiting_runner_cleanly(
    test_engine: Engine, db_session: Session
) -> None:
    wait = ControlledWait()
    control, _ = make_controller(test_engine, wait)
    await control.start(db_session)
    await wait.wait_for_next_interval()
    await control.shutdown()
    assert control.clock.state is SimulationClockState.STOPPED
    assert not control.runner_active


def test_tick_lock_prevents_simultaneous_execution(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    control = SimulationController(SimulationClock(initial_instant=INSTANT))
    control.clock.start()
    state_lock = Lock()
    first_entered = Event()
    release_first = Event()
    second_started = Event()
    active = 0
    maximum_active = 0
    invocations = 0

    def sequential_tick(db: Session, **_: object) -> TickResult:
        nonlocal active, invocations, maximum_active
        with state_lock:
            invocations += 1
            invocation = invocations
            active += 1
            maximum_active = max(maximum_active, active)
        if invocation == 1:
            first_entered.set()
            assert release_first.wait(timeout=1)
        with state_lock:
            active -= 1
        return TickResult(control.clock.current_instant, 0, 0, 0)

    monkeypatch.setattr("app.simulation.control.execute_tick", sequential_tick)
    first = Thread(target=control.tick, args=(db_session,))
    first.start()
    assert first_entered.wait(timeout=1)

    def run_second() -> None:
        second_started.set()
        control.tick(db_session)

    second = Thread(target=run_second)
    second.start()
    assert second_started.wait(timeout=1)
    assert maximum_active == 1
    release_first.set()
    threads = [first, second]
    for thread in threads:
        thread.join()
    assert maximum_active == 1


@pytest.mark.anyio
async def test_automatic_tick_preserves_energy_invariants(
    test_engine: Engine, db_session: Session
) -> None:
    station_id, session_id = seed_charging_session(
        db_session, grid_limit_kw=5, solar_peak_kw=3, requested_power_kw=9, max_power_kw=7
    )
    wait = ControlledWait()
    control, factory = make_controller(test_engine, wait)
    await control.start(db_session)
    await wait.complete_interval()
    await wait.wait_for_next_interval()
    await control.stop()

    with factory() as db:
        reading = db.scalar(select(EnergyReading).where(EnergyReading.session_id == session_id))
        station = db.get(ChargingStation, station_id)
        charging = db.get(ChargingSession, session_id)
        assert reading is not None and station is not None and charging is not None
        assert 0 <= reading.allocated_power_kw <= reading.requested_power_kw
        assert reading.allocated_power_kw <= 7
        assert reading.solar_power_kw + reading.grid_power_kw == pytest.approx(
            reading.allocated_power_kw
        )
        grid_total = db.scalar(
            select(func.sum(EnergyReading.grid_power_kw)).where(
                EnergyReading.timestamp == reading.timestamp
            )
        )
        assert grid_total is not None and grid_total <= station.grid_limit_kw
        assert charging.energy_consumed_kwh == pytest.approx(reading.interval_energy_kwh)
