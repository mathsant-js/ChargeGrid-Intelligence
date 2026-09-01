from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.simulation.clock import SimulationClock, SimulationClockState

FIXED_INSTANT = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def test_initial_state_uses_default_one_minute_tick() -> None:
    clock = SimulationClock(initial_instant=FIXED_INSTANT)

    assert clock.current_instant == FIXED_INSTANT
    assert clock.tick_duration == timedelta(minutes=1)
    assert clock.state is SimulationClockState.STOPPED


def test_start_and_stop_control_clock_state() -> None:
    clock = SimulationClock(initial_instant=FIXED_INSTANT)

    clock.start()
    assert clock.state is SimulationClockState.RUNNING

    clock.stop()
    assert clock.state is SimulationClockState.STOPPED


def test_advance_one_or_multiple_ticks_without_waiting() -> None:
    clock = SimulationClock(initial_instant=FIXED_INSTANT)
    clock.start()

    assert clock.advance() == FIXED_INSTANT + timedelta(minutes=1)
    assert clock.advance(ticks=3) == FIXED_INSTANT + timedelta(minutes=4)


def test_simulation_speed_accelerates_tick_duration() -> None:
    clock = SimulationClock(
        initial_instant=FIXED_INSTANT,
        simulation_speed=120,
        real_tick_interval=timedelta(seconds=2),
    )
    clock.start()

    assert clock.tick_duration == timedelta(minutes=4)
    assert clock.advance() == FIXED_INSTANT + timedelta(minutes=4)


def test_initial_instant_is_normalized_to_utc() -> None:
    source = datetime(2026, 9, 1, 9, 0, tzinfo=timezone(timedelta(hours=-3)))
    clock = SimulationClock(initial_instant=source)

    assert clock.current_instant == FIXED_INSTANT
    assert clock.current_instant.tzinfo is UTC
    clock.start()
    assert clock.advance().tzinfo is UTC


def test_fixed_initial_instant_produces_deterministic_results() -> None:
    first = SimulationClock(initial_instant=FIXED_INSTANT, simulation_speed=30)
    second = SimulationClock(initial_instant=FIXED_INSTANT, simulation_speed=30)
    first.start()
    second.start()

    assert first.advance(ticks=10) == second.advance(ticks=10)


@pytest.mark.parametrize("simulation_speed", [0, -1])
def test_rejects_non_positive_simulation_speed(simulation_speed: int) -> None:
    with pytest.raises(ValueError, match="simulation_speed must be positive"):
        SimulationClock(initial_instant=FIXED_INSTANT, simulation_speed=simulation_speed)


@pytest.mark.parametrize("interval", [timedelta(0), timedelta(microseconds=-1)])
def test_rejects_non_positive_real_tick_interval(interval: timedelta) -> None:
    with pytest.raises(ValueError, match="real_tick_interval must be positive"):
        SimulationClock(initial_instant=FIXED_INSTANT, real_tick_interval=interval)


def test_rejects_naive_initial_instant() -> None:
    with pytest.raises(ValueError, match="initial_instant must be timezone-aware"):
        SimulationClock(initial_instant=datetime(2026, 9, 1, 12, 0))


def test_stopped_clock_cannot_advance() -> None:
    clock = SimulationClock(initial_instant=FIXED_INSTANT)

    with pytest.raises(RuntimeError, match="must be running"):
        clock.advance()


@pytest.mark.parametrize("ticks", [0, -1, True])
def test_rejects_invalid_tick_count(ticks: int) -> None:
    clock = SimulationClock(initial_instant=FIXED_INSTANT)
    clock.start()

    with pytest.raises(ValueError, match="ticks must be a positive integer"):
        clock.advance(ticks=ticks)
