"""Automatic simulation runner coordination without wall-clock sleeps."""

import asyncio
from datetime import timedelta
from pathlib import Path
from threading import Event, Lock, Thread

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.energy import ChargingSession, EnergyReading, SolarReading
from app.models.infrastructure import ChargingStation
from app.models.simulation import SimulationState
from app.simulation.clock import SimulationClock, SimulationClockState
from app.simulation.control import SimulationController
from app.simulation.energy_data import (
    EnergyDataSource,
    SimulationEnergyDataProvider,
    TelemetryReplayEnergyDataProvider,
)
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


def test_controller_builds_configured_provider(tmp_path: Path) -> None:
    replay = tmp_path / "telemetry.csv"
    replay.write_text(
        "timestamp,station_code,pv_power_kw,grid_power_kw,load_power_kw,"
        "inverter_status,temperature_c,data_quality\n",
        encoding="utf-8",
    )

    curve = SimulationController._build_energy_data_provider("curve", replay)
    telemetry = SimulationController._build_energy_data_provider("telemetry_replay", replay)

    assert isinstance(curve, SimulationEnergyDataProvider)
    assert isinstance(telemetry, TelemetryReplayEnergyDataProvider)
    assert telemetry.source is EnergyDataSource.TELEMETRY_REPLAY


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


@pytest.mark.anyio
async def test_startup_restores_committed_clock_checkpoint_after_restart(
    test_engine: Engine, db_session: Session
) -> None:
    seed_charging_session(db_session)
    wait = ControlledWait()
    original, factory = make_controller(test_engine, wait)
    original.clock.start()
    original.tick(db_session)
    original.clock.stop()
    checkpoint = factory()
    state = checkpoint.query(SimulationState).one()
    expected_current = INSTANT + original.clock.tick_duration
    assert state.current_instant.replace(tzinfo=INSTANT.tzinfo) == expected_current
    assert state.last_tick.replace(tzinfo=INSTANT.tzinfo) == INSTANT
    checkpoint.close()

    # A separately constructed controller simulates a process restart.
    restarted, _ = make_controller(test_engine, ControlledWait())
    assert restarted.clock.current_instant == INSTANT
    assert restarted.last_tick is None
    await restarted.startup()
    assert restarted.clock.current_instant == expected_current
    assert restarted.last_tick == INSTANT
    assert restarted.clock.state is SimulationClockState.STOPPED


@pytest.mark.anyio
async def test_startup_does_not_rewind_configured_demo_clock_to_historical_solar_reading(
    test_engine: Engine, db_session: Session
) -> None:
    station = ChargingStation(name="Historical fixture", grid_limit_kw=60)
    db_session.add(station)
    db_session.flush()
    db_session.add(
        SolarReading(
            station_id=station.id,
            timestamp=INSTANT.replace(tzinfo=None) - timedelta(days=7),
            available_power_kw=20,
        )
    )
    db_session.commit()

    control, _ = make_controller(test_engine, ControlledWait())
    await control.startup()

    assert control.clock.current_instant == INSTANT
    assert control.last_tick is None


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


def test_independent_controllers_take_turns_from_durable_checkpoint(
    test_engine: Engine, db_session: Session
) -> None:
    """Separate worker controllers must process consecutive persisted instants."""
    first = SimulationController(SimulationClock(initial_instant=INSTANT))
    second = SimulationController(SimulationClock(initial_instant=INSTANT))
    first.clock.start()
    second.clock.start()

    assert first.tick(db_session) is not None
    assert second.tick(db_session) is not None

    with Session(test_engine) as db:
        state = db.scalar(select(SimulationState))
        assert state is not None
        assert state.last_tick.replace(tzinfo=INSTANT.tzinfo) == INSTANT + first.clock.tick_duration
        assert state.current_instant.replace(tzinfo=INSTANT.tzinfo) == (
            INSTANT + first.clock.tick_duration * 2
        )
    assert first.clock.current_instant == INSTANT + first.clock.tick_duration
    assert second.clock.current_instant == INSTANT + second.clock.tick_duration * 2


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
