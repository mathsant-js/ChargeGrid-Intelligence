"""Equal share power allocation for charging sessions at one station."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionPowerRequest:
    session_id: UUID
    requested_power_kw: float
    charger_max_power_kw: float
    vehicle_max_charge_power_kw: float


@dataclass(frozen=True, slots=True)
class PowerBreakdown:
    allocated_power_kw: float
    solar_power_kw: float
    grid_power_kw: float


class EqualSharePowerResolver:
    """Cap equal shares by each request, then use solar before grid power."""

    def resolve(
        self,
        *,
        station_id: UUID,
        grid_limit_kw: float,
        solar_available_kw: float,
        sessions: Sequence[SessionPowerRequest],
    ) -> dict[UUID, PowerBreakdown]:
        for value in (grid_limit_kw, solar_available_kw):
            if not math.isfinite(value) or value < 0:
                raise ValueError("station power must be finite and nonnegative")

        limits: dict[UUID, float] = {}
        for session in sessions:
            values = (
                session.requested_power_kw,
                session.charger_max_power_kw,
                session.vehicle_max_charge_power_kw,
            )
            if any(not math.isfinite(value) or value < 0 for value in values):
                raise ValueError("session power must be finite and nonnegative")
            if session.session_id in limits:
                raise ValueError("duplicate charging session")
            limits[session.session_id] = min(values)

        allocated = {session_id: 0.0 for session_id in limits}
        active = {session_id for session_id, limit in limits.items() if limit > 0}
        remaining = grid_limit_kw + solar_available_kw
        while active and remaining > 0:
            share = remaining / len(active)
            capped = {session_id for session_id in active if limits[session_id] <= share}
            if not capped:
                for session_id in active:
                    allocated[session_id] = share
                break
            for session_id in capped:
                allocated[session_id] = limits[session_id]
                remaining -= limits[session_id]
            active -= capped

        total_allocated = sum(allocated.values())
        solar_used = min(total_allocated, solar_available_kw)
        solar_fraction = solar_used / total_allocated if total_allocated else 0.0
        return {
            session_id: PowerBreakdown(
                allocated_power_kw=power,
                solar_power_kw=power * solar_fraction,
                grid_power_kw=power - power * solar_fraction,
            )
            for session_id, power in allocated.items()
        }
