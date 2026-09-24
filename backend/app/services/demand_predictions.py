"""Advisory demand inference; this module never writes charging allocations."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml.training import LoadedDemandModel, load_model_artifact
from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.energy import ChargingSession, ChargingSessionStatus, EnergyReading, SolarReading
from app.models.infrastructure import Charger, ChargingStation
from app.models.prediction import DemandPrediction, DemandRiskLevel, SystemConfiguration

FORECAST_HORIZON_MINUTES = 60

RECOMMENDATIONS = {
    DemandRiskLevel.LOW: "Demanda prevista dentro da faixa normal. Mantenha o monitoramento.",
    DemandRiskLevel.MEDIUM: (
        "Demanda prevista elevada. Monitore novas sessões e a capacidade disponível."
    ),
    DemandRiskLevel.HIGH: (
        "Alta probabilidade de utilização próxima ao limite. "
        "Considere restringir a potência de novas sessões."
    ),
}


class PredictionDataError(RuntimeError):
    """Raised when causal inference features cannot be assembled."""


@dataclass(frozen=True, slots=True)
class InferenceFeatures:
    hour: int
    day_of_week: int
    is_weekend: bool
    active_sessions: int
    current_demand_kw: float
    historical_avg_demand_kw: float
    solar_available_kw: float


def classify_risk(
    predicted_demand_kw: float,
    capacity_kw: float,
    *,
    medium_threshold: float,
    high_threshold: float,
) -> DemandRiskLevel:
    ratio = predicted_demand_kw / capacity_kw
    if ratio >= high_threshold:
        return DemandRiskLevel.HIGH
    if ratio >= medium_threshold:
        return DemandRiskLevel.MEDIUM
    return DemandRiskLevel.LOW


def recommendation_for(risk_level: DemandRiskLevel) -> str:
    return RECOMMENDATIONS[risk_level]


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def build_inference_features(
    db: Session, station_id: UUID, generated_at: datetime
) -> tuple[InferenceFeatures, float]:
    """Build only from observations whose timestamps are no later than prediction time."""

    solar = db.scalar(
        select(SolarReading)
        .where(SolarReading.station_id == station_id, SolarReading.timestamp <= generated_at)
        .order_by(SolarReading.timestamp.desc(), SolarReading.id.desc())
        .limit(1)
    )
    if solar is None:
        raise PredictionDataError("insufficient features: no solar observation is available")

    aggregates = db.execute(
        select(EnergyReading.timestamp, func.sum(EnergyReading.allocated_power_kw))
        .join(ChargingSession, EnergyReading.session_id == ChargingSession.id)
        .join(Charger, ChargingSession.charger_id == Charger.id)
        .where(Charger.station_id == station_id, EnergyReading.timestamp <= generated_at)
        .group_by(EnergyReading.timestamp)
        .order_by(EnergyReading.timestamp)
    ).all()
    if not aggregates:
        raise PredictionDataError("insufficient features: no demand observation is available")

    _, current_demand = aggregates[-1]
    historical = [
        float(demand)
        for timestamp, demand in aggregates[:-1]
        if _as_utc(timestamp).weekday() == generated_at.weekday()
        and _as_utc(timestamp).hour == generated_at.hour
    ]
    if not historical:
        raise PredictionDataError(
            "insufficient features: no prior observation exists for this weekday and hour"
        )
    active_sessions = db.scalar(
        select(func.count(ChargingSession.id))
        .join(Charger, ChargingSession.charger_id == Charger.id)
        .where(
            Charger.station_id == station_id,
            ChargingSession.status == ChargingSessionStatus.CHARGING,
        )
    ) or 0
    solar_available = float(solar.available_power_kw)
    return (
        InferenceFeatures(
            hour=generated_at.hour,
            day_of_week=generated_at.weekday(),
            is_weekend=generated_at.weekday() >= 5,
            active_sessions=int(active_sessions),
            current_demand_kw=float(current_demand),
            historical_avg_demand_kw=sum(historical) / len(historical),
            solar_available_kw=solar_available,
        ),
        solar_available,
    )


def run_demand_prediction(
    db: Session,
    *,
    station: ChargingStation,
    configuration: SystemConfiguration,
    artifact_path: Path,
    generated_at: datetime | None = None,
) -> DemandPrediction:
    """Run and persist advisory inference without invoking the power allocator."""

    instant = _as_utc(generated_at or datetime.now(UTC))
    features, solar_available = build_inference_features(db, station.id, instant)
    loaded: LoadedDemandModel = load_model_artifact(artifact_path)
    predicted_demand_kw = max(0.0, loaded.predict([features])[0])
    capacity_kw = station.grid_limit_kw + solar_available
    risk_level = classify_risk(
        predicted_demand_kw,
        capacity_kw,
        medium_threshold=configuration.medium_peak_threshold,
        high_threshold=configuration.high_peak_threshold,
    )
    previous_risk = db.scalar(
        select(DemandPrediction.risk_level)
        .where(DemandPrediction.station_id == station.id)
        .order_by(DemandPrediction.generated_at.desc(), DemandPrediction.id.desc())
        .limit(1)
    )
    prediction = DemandPrediction(
        station_id=station.id,
        generated_at=instant,
        prediction_for=instant + timedelta(minutes=FORECAST_HORIZON_MINUTES),
        predicted_demand_kw=predicted_demand_kw,
        capacity_kw=capacity_kw,
        risk_level=risk_level,
        model_version=loaded.metadata.model_version,
    )
    db.add(prediction)
    if risk_level == DemandRiskLevel.HIGH and previous_risk != DemandRiskLevel.HIGH:
        db.add(
            Alert(
                station_id=station.id,
                type=AlertType.PEAK_RISK,
                severity=AlertSeverity.CRITICAL,
                title="Peak demand risk",
                message=recommendation_for(risk_level),
                created_at=instant,
            )
        )
    return prediction
