"""Train, evaluate, persist, and load the Phase 7 demand model."""

import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from app.ml.baseline import RegressionMetrics, chronological_split, regression_metrics
from app.ml.dataset import DemandDatasetRow

logger = logging.getLogger(__name__)

MODEL_VERSION = "1.0.0"
MODEL_FEATURES = (
    "hour",
    "day_of_week",
    "is_weekend",
    "active_sessions",
    "current_demand_kw",
    "historical_avg_demand_kw",
    "solar_available_kw",
)
TARGET_COLUMN = "demand_kw_next_60_minutes"
ARTIFACT_FORMAT_VERSION = 1


class ModelArtifactError(RuntimeError):
    """Base error for model artifact failures."""


class ModelArtifactNotFoundError(ModelArtifactError):
    """Raised when the configured model artifact does not exist."""


class IncompatibleModelArtifactError(ModelArtifactError):
    """Raised when artifact features or structure are incompatible."""


@dataclass(frozen=True, slots=True)
class TrainingPeriod:
    start: datetime
    end: datetime
    rows: int


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    artifact_format_version: int
    model_version: str
    algorithm: str
    features: tuple[str, ...]
    target: str
    training_period: TrainingPeriod
    test_period: TrainingPeriod
    metrics: RegressionMetrics


@dataclass(frozen=True, slots=True)
class ModelComparison:
    model: RegressionMetrics
    baseline: RegressionMetrics
    mae_improvement: float
    rmse_improvement: float
    r2_improvement: float


@dataclass(frozen=True, slots=True)
class TrainingResult:
    metadata: ModelMetadata
    comparison: ModelComparison


@dataclass(frozen=True, slots=True)
class LoadedDemandModel:
    model: RandomForestRegressor
    metadata: ModelMetadata

    def predict(self, rows: Sequence[DemandDatasetRow]) -> list[float]:
        frame = _feature_frame(rows, self.metadata.features)
        return [float(value) for value in self.model.predict(frame)]


def _feature_frame(
    rows: Sequence[DemandDatasetRow], features: Sequence[str] = MODEL_FEATURES
) -> pd.DataFrame:
    return pd.DataFrame(
        [{feature: getattr(row, feature) for feature in features} for row in rows],
        columns=list(features),
    )


def _period(rows: Sequence[DemandDatasetRow]) -> TrainingPeriod:
    return TrainingPeriod(start=rows[0].timestamp, end=rows[-1].timestamp, rows=len(rows))


def train_and_evaluate(
    rows: Sequence[DemandDatasetRow],
    *,
    baseline_metrics: RegressionMetrics,
    artifact_path: Path,
    test_fraction: float = 0.2,
    random_state: int = 42,
    n_estimators: int = 200,
) -> TrainingResult:
    """Train only on the chronological training window and persist a Joblib bundle."""

    train, test = chronological_split(rows, test_fraction)
    logger.info(
        "Starting demand model training: version=%s algorithm=RandomForestRegressor "
        "train_rows=%d test_rows=%d train_start=%s train_end=%s",
        MODEL_VERSION,
        len(train),
        len(test),
        train[0].timestamp.isoformat(),
        train[-1].timestamp.isoformat(),
    )
    model = RandomForestRegressor(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(
        _feature_frame(train),
        [row.demand_kw_next_60_minutes for row in train],
    )
    predictions = model.predict(_feature_frame(test))
    metrics = regression_metrics(
        [row.demand_kw_next_60_minutes for row in test],
        [float(value) for value in predictions],
    )
    metadata = ModelMetadata(
        artifact_format_version=ARTIFACT_FORMAT_VERSION,
        model_version=MODEL_VERSION,
        algorithm="RandomForestRegressor",
        features=MODEL_FEATURES,
        target=TARGET_COLUMN,
        training_period=_period(train),
        test_period=_period(test),
        metrics=metrics,
    )
    comparison = ModelComparison(
        model=metrics,
        baseline=baseline_metrics,
        mae_improvement=baseline_metrics.mae - metrics.mae,
        rmse_improvement=baseline_metrics.rmse - metrics.rmse,
        r2_improvement=metrics.r2 - baseline_metrics.r2,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "metadata": asdict(metadata)}, artifact_path)
    logger.info(
        "Demand model training completed: version=%s mae=%.6f rmse=%.6f r2=%.6f",
        MODEL_VERSION,
        metrics.mae,
        metrics.rmse,
        metrics.r2,
    )
    return TrainingResult(metadata=metadata, comparison=comparison)


def _metadata_from_dict(value: object) -> ModelMetadata:
    if not isinstance(value, dict):
        raise IncompatibleModelArtifactError("artifact metadata is missing or invalid")
    try:
        data = cast(dict[str, Any], value)
        return ModelMetadata(
            artifact_format_version=int(data["artifact_format_version"]),
            model_version=str(data["model_version"]),
            algorithm=str(data["algorithm"]),
            features=tuple(data["features"]),
            target=str(data["target"]),
            training_period=TrainingPeriod(**data["training_period"]),
            test_period=TrainingPeriod(**data["test_period"]),
            metrics=RegressionMetrics(**data["metrics"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise IncompatibleModelArtifactError("artifact metadata is incomplete") from error


def load_model_artifact(
    artifact_path: Path,
    *,
    expected_features: Sequence[str] = MODEL_FEATURES,
) -> LoadedDemandModel:
    """Load a model only when its format and ordered feature contract match."""

    if not artifact_path.is_file():
        raise ModelArtifactNotFoundError(f"model artifact not found: {artifact_path}")
    try:
        bundle = joblib.load(artifact_path)
    except Exception as error:
        raise IncompatibleModelArtifactError("model artifact could not be loaded") from error
    if not isinstance(bundle, dict) or "model" not in bundle:
        raise IncompatibleModelArtifactError("artifact model is missing or invalid")
    metadata = _metadata_from_dict(bundle.get("metadata"))
    expected = tuple(expected_features)
    if metadata.artifact_format_version != ARTIFACT_FORMAT_VERSION:
        raise IncompatibleModelArtifactError("artifact format version is incompatible")
    if metadata.features != expected:
        raise IncompatibleModelArtifactError(
            f"artifact features are incompatible: expected {expected}, got {metadata.features}"
        )
    model = bundle["model"]
    if not isinstance(model, RandomForestRegressor):
        raise IncompatibleModelArtifactError("artifact model type is incompatible")
    if getattr(model, "n_features_in_", None) != len(expected):
        raise IncompatibleModelArtifactError("artifact model feature count is incompatible")
    return LoadedDemandModel(model=model, metadata=metadata)
