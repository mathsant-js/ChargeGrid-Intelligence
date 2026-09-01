from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select

from app.api.routes.common import DbSession, commit_or_conflict, get_or_404
from app.models.infrastructure import ChargingStation
from app.models.prediction import DemandPrediction, SystemConfiguration
from app.schemas.prediction import (
    DemandPredictionCreate,
    DemandPredictionResponse,
    SystemConfigurationCreate,
    SystemConfigurationResponse,
    SystemConfigurationUpdate,
    SystemConfigurationValues,
)

predictions_router = APIRouter(prefix="/predictions", tags=["predictions"])
configuration_router = APIRouter(prefix="/system-configuration", tags=["configuration"])


@predictions_router.get("/demand", response_model=DemandPredictionResponse)
async def get_latest_demand_prediction(
    db: DbSession, station_id: UUID | None = None
) -> DemandPrediction:
    statement = select(DemandPrediction)
    if station_id is not None:
        statement = statement.where(DemandPrediction.station_id == station_id)
    prediction = db.scalar(
        statement.order_by(
            DemandPrediction.generated_at.desc(), DemandPrediction.id.desc()
        ).limit(1)
    )
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return prediction


@predictions_router.post(
    "/demand", response_model=DemandPredictionResponse, status_code=status.HTTP_201_CREATED
)
async def create_demand_prediction(
    payload: DemandPredictionCreate, db: DbSession
) -> DemandPrediction:
    get_or_404(db, ChargingStation, payload.station_id)
    prediction = DemandPrediction(**payload.model_dump())
    db.add(prediction)
    commit_or_conflict(db)
    db.refresh(prediction)
    return prediction


@configuration_router.get("", response_model=SystemConfigurationResponse)
async def get_system_configuration(db: DbSession) -> SystemConfiguration:
    configuration = db.scalar(select(SystemConfiguration).limit(1))
    if configuration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    return configuration


@configuration_router.post(
    "", response_model=SystemConfigurationResponse, status_code=status.HTTP_201_CREATED
)
async def create_system_configuration(
    payload: SystemConfigurationCreate, db: DbSession
) -> SystemConfiguration:
    if db.scalar(select(SystemConfiguration.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="System configuration already exists"
        )
    configuration = SystemConfiguration(**payload.model_dump())
    db.add(configuration)
    commit_or_conflict(db)
    db.refresh(configuration)
    return configuration


@configuration_router.patch("", response_model=SystemConfigurationResponse)
async def update_system_configuration(
    payload: SystemConfigurationUpdate, db: DbSession
) -> SystemConfiguration:
    configuration = await get_system_configuration(db)
    values = {
        "simulation_speed": configuration.simulation_speed,
        "grid_emission_factor_kg_per_kwh": configuration.grid_emission_factor_kg_per_kwh,
        "high_demand_threshold": configuration.high_demand_threshold,
        "medium_peak_threshold": configuration.medium_peak_threshold,
        "high_peak_threshold": configuration.high_peak_threshold,
    }
    values.update(payload.model_dump(exclude_unset=True, exclude_none=True))
    try:
        validated = SystemConfigurationValues.model_validate(values)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Peak thresholds must satisfy medium < high",
        ) from exc
    for field, value in validated.model_dump().items():
        setattr(configuration, field, value)
    commit_or_conflict(db)
    db.refresh(configuration)
    return configuration
