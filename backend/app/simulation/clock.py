"""Deterministic clock primitives for the equipment simulator."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

DEFAULT_SIMULATION_SPEED = 60
DEFAULT_REAL_TICK_INTERVAL = timedelta(seconds=1)


class SimulationClockState(StrEnum):
    """Lifecycle state of a simulation clock."""

    STOPPED = "STOPPED"
    RUNNING = "RUNNING"


@dataclass(slots=True)
class SimulationClock:
    """A deterministic clock advanced explicitly by simulation ticks.

    ``simulation_speed`` is the number of simulated seconds represented by one
    real second and is intended to receive ``SystemConfiguration.simulation_speed``.
    The defaults therefore implement the initial 1 real second = 1 simulated
    minute configuration without coupling the clock to persistence or a run loop.
    """

    initial_instant: datetime
    simulation_speed: int = DEFAULT_SIMULATION_SPEED
    real_tick_interval: timedelta = DEFAULT_REAL_TICK_INTERVAL
    _current_instant: datetime = field(init=False, repr=False)
    state: SimulationClockState = field(init=False, default=SimulationClockState.STOPPED)

    def __post_init__(self) -> None:
        if self.initial_instant.tzinfo is None or self.initial_instant.utcoffset() is None:
            raise ValueError("initial_instant must be timezone-aware")
        if self.simulation_speed <= 0:
            raise ValueError("simulation_speed must be positive")
        if self.real_tick_interval <= timedelta(0):
            raise ValueError("real_tick_interval must be positive")

        self.initial_instant = self.initial_instant.astimezone(UTC)
        self._current_instant = self.initial_instant

    @property
    def current_instant(self) -> datetime:
        """Return the current simulated instant as a read-only UTC value."""

        return self._current_instant

    @property
    def tick_duration(self) -> timedelta:
        """Return the simulated time represented by one execution tick."""

        return self.real_tick_interval * self.simulation_speed

    def start(self) -> None:
        """Put the clock in the running state."""

        self.state = SimulationClockState.RUNNING

    def stop(self) -> None:
        """Put the clock in the stopped state."""

        self.state = SimulationClockState.STOPPED

    def advance(self, ticks: int = 1) -> datetime:
        """Advance a running clock by an explicit number of ticks."""

        if self.state is not SimulationClockState.RUNNING:
            raise RuntimeError("simulation clock must be running to advance")
        if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks <= 0:
            raise ValueError("ticks must be a positive integer")

        self._current_instant += self.tick_duration * ticks
        return self._current_instant
