from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PowerRequest:
    session_id: str
    requested_power_kw: float
    charger_max_power_kw: float
    vehicle_max_power_kw: float


@dataclass(frozen=True, slots=True)
class PowerAllocation:
    session_id: str
    requested_power_kw: float
    allocated_power_kw: float
    solar_power_kw: float
    grid_power_kw: float


@dataclass(frozen=True, slots=True)
class AllocationResult:
    allocations: tuple[PowerAllocation, ...]
    total_requested_kw: float
    total_allocated_kw: float
    solar_used_kw: float
    grid_used_kw: float


def allocate_power(
    requests: list[PowerRequest], *, grid_limit_kw: float, solar_available_kw: float
) -> AllocationResult:
    """Apply equal-share allocation and prioritize solar without exceeding safety limits."""
    if grid_limit_kw < 0 or solar_available_kw < 0:
        raise ValueError("Power availability cannot be negative")

    capped_requests = {
        request.session_id: max(
            0.0,
            min(
                request.requested_power_kw,
                request.charger_max_power_kw,
                request.vehicle_max_power_kw,
            ),
        )
        for request in requests
    }
    remaining = grid_limit_kw + solar_available_kw
    pending = set(capped_requests)
    allocated = {session_id: 0.0 for session_id in capped_requests}

    while pending and remaining > 1e-9:
        share = remaining / len(pending)
        fulfilled: set[str] = set()
        for session_id in pending:
            need = capped_requests[session_id] - allocated[session_id]
            amount = min(share, need)
            allocated[session_id] += amount
            remaining -= amount
            if need <= share + 1e-9:
                fulfilled.add(session_id)
        if not fulfilled:
            break
        pending -= fulfilled

    total_allocated = sum(allocated.values())
    solar_used = min(total_allocated, solar_available_kw)
    solar_ratio = solar_used / total_allocated if total_allocated else 0.0
    allocations = tuple(
        PowerAllocation(
            session_id=request.session_id,
            requested_power_kw=capped_requests[request.session_id],
            allocated_power_kw=allocated[request.session_id],
            solar_power_kw=allocated[request.session_id] * solar_ratio,
            grid_power_kw=allocated[request.session_id] * (1 - solar_ratio),
        )
        for request in requests
    )
    return AllocationResult(
        allocations=allocations,
        total_requested_kw=sum(capped_requests.values()),
        total_allocated_kw=total_allocated,
        solar_used_kw=solar_used,
        grid_used_kw=total_allocated - solar_used,
    )


def interval_energy_kwh(power_kw: float, interval_minutes: float) -> float:
    if power_kw < 0 or interval_minutes < 0:
        raise ValueError("Power and interval cannot be negative")
    return power_kw * interval_minutes / 60
