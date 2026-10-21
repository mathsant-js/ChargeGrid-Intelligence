from datetime import datetime

from pydantic import BaseModel

from app.simulation.clock import SimulationClockState
from app.simulation.energy_data import EnergyDataSource


class SimulationStatusResponse(BaseModel):
    state: SimulationClockState
    current_instant: datetime
    tick_duration_seconds: float
    simulation_speed: int
    last_tick: datetime | None
    energy_data_source: EnergyDataSource


class SimulationTickResponse(BaseModel):
    timestamp: datetime
    stations_processed: int
    energy_readings_created: int
    stations_already_processed: int
    current_instant: datetime
