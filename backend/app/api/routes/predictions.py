from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select

from app.api.dependencies import AdminUser, CurrentUser
from app.api.routes.common import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    DbSession,
    commit_or_conflict,
    get_or_404,
)
from app.core.config import get_settings
from app.ml.training import ModelArtifactError
from app.models.infrastructure import ChargingStation
from app.models.prediction import DemandPrediction, SystemConfiguration
from app.schemas.common import ErrorResponse
from app.schemas.prediction import (
    DemandPredictionCreate,
    DemandPredictionResponse,
    DemandPredictionRun,
    SystemConfigurationCreate,
    SystemConfigurationResponse,
    SystemConfigurationUpdate,
    SystemConfigurationValues,
)
from app.services.demand_predictions import PredictionDataError, run_demand_prediction
from app.simulation.control import SimulationController, get_simulation_controller

predictions_router = APIRouter(prefix="/predictions", tags=["predictions"])
configuration_router = APIRouter(prefix="/system-configuration", tags=["configuration"])
Controller = Annotated[SimulationController, Depends(get_simulation_controller)]


@predictions_router.get(
    "/demand",
    response_model=DemandPredictionResponse,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE,
)
async def get_latest_demand_prediction(
    db: DbSession, _: CurrentUser, station_id: UUID | None = None
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
    "/demand",
    response_model=DemandPredictionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE,
)
async def create_demand_prediction(
    payload: DemandPredictionCreate, db: DbSession, _: AdminUser
) -> DemandPrediction:
    get_or_404(db, ChargingStation, payload.station_id)
    prediction = DemandPrediction(**payload.model_dump())
    db.add(prediction)
    commit_or_conflict(db)
    db.refresh(prediction)
    return prediction


@predictions_router.post(
    "/demand/run",
    response_model=DemandPredictionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE | {
        422: {"model": ErrorResponse, "description": "Inference features are insufficient"},
        503: {"model": ErrorResponse, "description": "Demand model is unavailable"},
    },
)
async def execute_demand_prediction(
    payload: DemandPredictionRun,
    db: DbSession,
    _: AdminUser,
    control: Controller,
) -> DemandPrediction:
    station = db.scalar(
        select(ChargingStation)
        .where(ChargingStation.id == payload.station_id)
        .with_for_update()
    )
    if station is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    configuration = db.scalar(select(SystemConfiguration).limit(1))
    if configuration is None:
        raise HTTPException(status_code=404, detail="Configuration not found")
    try:
        settings = get_settings()
        prediction = run_demand_prediction(
            db,
            station=station,
            configuration=configuration,
            artifact_path=settings.demand_model_path,
            generated_at=(
                control.clock.current_instant
                if settings.demo_simulation_start_utc is not None
                else None
            ),
        )
    except PredictionDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ModelArtifactError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    commit_or_conflict(db)
    db.refresh(prediction)
    return prediction


@configuration_router.get(
    "",
    response_model=SystemConfigurationResponse,
    responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE,
)
async def get_system_configuration(db: DbSession, _: AdminUser) -> SystemConfiguration:
    configuration = db.scalar(select(SystemConfiguration).limit(1))
    if configuration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    return configuration


@configuration_router.post(
    "",
    response_model=SystemConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | CONFLICT_RESPONSE,
)
async def create_system_configuration(
    payload: SystemConfigurationCreate, db: DbSession, _: AdminUser
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


@configuration_router.patch(
    "",
    response_model=SystemConfigurationResponse,
    responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE,
)
async def update_system_configuration(
    payload: SystemConfigurationUpdate, db: DbSession, admin: AdminUser
) -> SystemConfiguration:
    configuration = await get_system_configuration(db, admin)
    values = {
        "simulation_speed": configuration.simulation_speed,
        "grid_emission_factor_kg_per_kwh": configuration.grid_emission_factor_kg_per_kwh,
        "high_demand_threshold": configuration.high_demand_threshold,
        "high_solar_availability_threshold": (
            configuration.high_solar_availability_threshold
        ),
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
