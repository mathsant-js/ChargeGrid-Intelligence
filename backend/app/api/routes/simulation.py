"""Administrative control of the automatic Phase 3 simulator."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import AdminUser
from app.api.routes.common import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    DbSession,
)
from app.schemas.simulation import SimulationStatusResponse, SimulationTickResponse
from app.simulation.control import SimulationController, get_simulation_controller

router = APIRouter(prefix="/simulation", tags=["simulation"])
Controller = Annotated[SimulationController, Depends(get_simulation_controller)]
AUTH_RESPONSES = UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE


def _status(control: SimulationController) -> SimulationStatusResponse:
    with control.lock:
        return SimulationStatusResponse(
            state=control.clock.state,
            current_instant=control.clock.current_instant,
            tick_duration_seconds=control.clock.tick_duration.total_seconds(),
            simulation_speed=control.clock.simulation_speed,
            last_tick=control.last_tick,
        )


@router.get("/status", response_model=SimulationStatusResponse, responses=AUTH_RESPONSES)
async def simulation_status(_: AdminUser, control: Controller) -> SimulationStatusResponse:
    """Return this API process's clock state and most recent successful tick."""
    return _status(control)


@router.post("/start", response_model=SimulationStatusResponse, responses=AUTH_RESPONSES)
async def start_simulation(
    db: DbSession, _: AdminUser, control: Controller
) -> SimulationStatusResponse:
    """Idempotently start automatic ticks and load the configured simulation speed."""
    await control.start(db)
    return _status(control)


@router.post("/stop", response_model=SimulationStatusResponse, responses=AUTH_RESPONSES)
async def stop_simulation(_: AdminUser, control: Controller) -> SimulationStatusResponse:
    """Idempotently stop automatic ticks and wait for the runner to exit."""
    await control.stop()
    return _status(control)


@router.post(
    "/reset",
    response_model=SimulationStatusResponse,
    responses=AUTH_RESPONSES | CONFLICT_RESPONSE,
)
async def reset_simulation(
    db: DbSession, _: AdminUser, control: Controller
) -> SimulationStatusResponse:
    """While stopped, clear clock metadata and move beyond saved readings without deleting data."""
    if not control.reset(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Stop simulation before reset"
        )
    return _status(control)


@router.post(
    "/ticks",
    response_model=SimulationTickResponse,
    responses=AUTH_RESPONSES | CONFLICT_RESPONSE,
)
async def run_simulation_tick(
    db: DbSession, _: AdminUser, control: Controller
) -> SimulationTickResponse:
    """Run exactly one transactional tick while RUNNING."""
    result = control.tick(db)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Simulation is stopped")
    return SimulationTickResponse(
        timestamp=result.timestamp,
        stations_processed=result.stations_processed,
        energy_readings_created=result.energy_readings_created,
        stations_already_processed=result.stations_already_processed,
        current_instant=control.clock.current_instant,
    )
