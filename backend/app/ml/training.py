"""Compare, select, persist, and load simple demand forecasters."""

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)

from app.ml.baseline import RegressionMetrics, chronological_split, regression_metrics
from app.ml.dataset import DemandDatasetRow

logger = logging.getLogger(__name__)
MODEL_VERSION = "2.0.0"
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
ARTIFACT_FORMAT_VERSION = 3
SELECTION_METRIC = "rmse"
BASELINE_NAME = "HistoricalMeanBaseline"


class ModelArtifactError(RuntimeError):
    pass


class ModelArtifactNotFoundError(ModelArtifactError):
    pass


class IncompatibleModelArtifactError(ModelArtifactError):
    pass


@dataclass(frozen=True, slots=True)
class TrainingPeriod:
    start: datetime
    end: datetime
    rows: int


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    artifact_format_version: int
    sklearn_version: str
    model_version: str
    algorithm: str
    features: tuple[str, ...]
    target: str
    forecast_horizon_minutes: int
    random_state: int
    training_period: TrainingPeriod
    test_period: TrainingPeriod
    metrics: RegressionMetrics
    candidate_metrics: dict[str, RegressionMetrics]
    selection_metric: str


@dataclass(frozen=True, slots=True)
class ModelComparison:
    candidates: dict[str, RegressionMetrics]
    winner: str
    selection_metric: str
    baseline_won: bool


@dataclass(frozen=True, slots=True)
class SegmentEvaluation:
    by_hour: dict[str, RegressionMetrics]
    by_demand_band: dict[str, RegressionMetrics]


@dataclass(frozen=True, slots=True)
class TrainingResult:
    metadata: ModelMetadata
    comparison: ModelComparison
    segments: SegmentEvaluation


class DemandFeatureRow(Protocol):
    @property
    def hour(self) -> int: ...
    @property
    def day_of_week(self) -> int: ...
    @property
    def is_weekend(self) -> bool: ...
    @property
    def active_sessions(self) -> int: ...
    @property
    def current_demand_kw(self) -> float: ...
    @property
    def historical_avg_demand_kw(self) -> float: ...
    @property
    def solar_available_kw(self) -> float: ...


@dataclass
class HistoricalMeanBaseline:
    """Persistable implementation of the SPEC hour/day historical baseline."""

    averages: dict[tuple[int, int], float]
    global_average: float
    n_features_in_: int = len(MODEL_FEATURES)

    @classmethod
    def fit(cls, rows: Sequence[DemandDatasetRow]) -> "HistoricalMeanBaseline":
        totals: defaultdict[tuple[int, int], float] = defaultdict(float)
        counts: defaultdict[tuple[int, int], int] = defaultdict(int)
        for row in rows:
            key = (row.day_of_week, row.hour)
            totals[key] += row.demand_kw_next_60_minutes
            counts[key] += 1
        return cls(
            {key: totals[key] / count for key, count in counts.items()},
            sum(row.demand_kw_next_60_minutes for row in rows) / len(rows),
        )

    def predict(self, frame: pd.DataFrame) -> list[float]:
        return [
            self.averages.get((int(row.day_of_week), int(row.hour)), self.global_average)
            for row in frame.itertuples(index=False)
        ]


type SupportedModel = (
    HistoricalMeanBaseline
    | RandomForestRegressor
    | ExtraTreesRegressor
    | HistGradientBoostingRegressor
)


@dataclass(frozen=True, slots=True)
class LoadedDemandModel:
    model: SupportedModel
    metadata: ModelMetadata

    def predict(self, rows: Sequence[DemandFeatureRow]) -> list[float]:
        return [
            max(0.0, float(value))
            for value in self.model.predict(_feature_frame(rows, self.metadata.features))
        ]


def _feature_frame(
    rows: Sequence[DemandFeatureRow], features: Sequence[str] = MODEL_FEATURES
) -> pd.DataFrame:
    return pd.DataFrame(
        [{feature: getattr(row, feature) for feature in features} for row in rows],
        columns=list(features),
    )


def _period(rows: Sequence[DemandDatasetRow]) -> TrainingPeriod:
    return TrainingPeriod(start=rows[0].timestamp, end=rows[-1].timestamp, rows=len(rows))


def _candidate_models(random_state: int, n_estimators: int) -> dict[str, SupportedModel]:
    return {
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=n_estimators,
            min_samples_leaf=8,
            max_features=0.8,
            random_state=random_state,
            n_jobs=1,
        ),
        "ExtraTreesRegressor": ExtraTreesRegressor(
            n_estimators=n_estimators,
            min_samples_leaf=8,
            max_features=0.8,
            random_state=random_state,
            n_jobs=1,
        ),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(
            max_iter=min(n_estimators, 120),
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=random_state,
        ),
    }


def _segment_metrics(
    test: Sequence[DemandDatasetRow], predictions: Sequence[float]
) -> SegmentEvaluation:
    hour_groups: defaultdict[str, list[tuple[float, float]]] = defaultdict(list)
    band_groups: defaultdict[str, list[tuple[float, float]]] = defaultdict(list)
    for row, predicted in zip(test, predictions, strict=True):
        actual = row.demand_kw_next_60_minutes
        hour_groups[f"{row.hour:02d}:00"].append((actual, predicted))
        band = "low_<50kw" if actual < 50 else "medium_50-100kw" if actual < 100 else "high_>=100kw"
        band_groups[band].append((actual, predicted))

    def calculate(groups: dict[str, list[tuple[float, float]]]) -> dict[str, RegressionMetrics]:
        return {
            name: regression_metrics([pair[0] for pair in pairs], [pair[1] for pair in pairs])
            for name, pairs in groups.items()
        }

    return SegmentEvaluation(calculate(hour_groups), calculate(band_groups))


def train_and_evaluate(
    rows: Sequence[DemandDatasetRow],
    *,
    baseline_metrics: RegressionMetrics,
    artifact_path: Path,
    test_fraction: float = 0.2,
    random_state: int = 42,
    n_estimators: int = 120,
) -> TrainingResult:
    """Evaluate one baseline plus three fixed classical candidates and persist the winner."""

    train, test = chronological_split(rows, test_fraction)
    x_train, x_test = _feature_frame(train), _feature_frame(test)
    y_train = [row.demand_kw_next_60_minutes for row in train]
    y_test = [row.demand_kw_next_60_minutes for row in test]
    models: dict[str, Any] = {BASELINE_NAME: HistoricalMeanBaseline.fit(train)}
    models.update(_candidate_models(random_state, n_estimators))
    metrics_by_name: dict[str, RegressionMetrics] = {}
    predictions_by_name: dict[str, list[float]] = {}
    for name, model in models.items():
        if name != BASELINE_NAME:
            model.fit(x_train, y_train)
        predictions = [float(value) for value in model.predict(x_test)]
        predictions_by_name[name] = predictions
        metrics_by_name[name] = regression_metrics(y_test, predictions)
    if metrics_by_name[BASELINE_NAME] != baseline_metrics:
        raise ValueError("baseline metrics must use the same chronological split")
    winner = min(metrics_by_name, key=lambda name: metrics_by_name[name].rmse)
    metadata = ModelMetadata(
        artifact_format_version=ARTIFACT_FORMAT_VERSION,
        sklearn_version=sklearn.__version__,
        model_version=MODEL_VERSION,
        algorithm=winner,
        features=MODEL_FEATURES,
        target=TARGET_COLUMN,
        forecast_horizon_minutes=60,
        random_state=random_state,
        training_period=_period(train),
        test_period=_period(test),
        metrics=metrics_by_name[winner],
        candidate_metrics=metrics_by_name,
        selection_metric=SELECTION_METRIC,
    )
    comparison = ModelComparison(metrics_by_name, winner, SELECTION_METRIC, winner == BASELINE_NAME)
    segments = _segment_metrics(test, predictions_by_name[winner])
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": models[winner], "metadata": asdict(metadata)}, artifact_path)
    logger.info(
        "Demand model selection completed: winner=%s rmse=%.6f", winner, metadata.metrics.rmse
    )
    return TrainingResult(metadata, comparison, segments)


def _metadata_from_dict(value: object) -> ModelMetadata:
    if not isinstance(value, dict):
        raise IncompatibleModelArtifactError("artifact metadata is missing or invalid")
    try:
        data = cast(dict[str, Any], value)
        return ModelMetadata(
            artifact_format_version=int(data["artifact_format_version"]),
            sklearn_version=str(data["sklearn_version"]),
            model_version=str(data["model_version"]),
            algorithm=str(data["algorithm"]),
            features=tuple(data["features"]),
            target=str(data["target"]),
            forecast_horizon_minutes=int(data["forecast_horizon_minutes"]),
            random_state=int(data["random_state"]),
            training_period=TrainingPeriod(**data["training_period"]),
            test_period=TrainingPeriod(**data["test_period"]),
            metrics=RegressionMetrics(**data["metrics"]),
            candidate_metrics={
                name: RegressionMetrics(**metrics)
                for name, metrics in data["candidate_metrics"].items()
            },
            selection_metric=str(data["selection_metric"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise IncompatibleModelArtifactError("artifact metadata is incomplete") from error


def load_model_artifact(
    artifact_path: Path, *, expected_features: Sequence[str] = MODEL_FEATURES
) -> LoadedDemandModel:
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
    if metadata.sklearn_version != sklearn.__version__:
        raise IncompatibleModelArtifactError(
            "artifact scikit-learn version is incompatible: "
            f"expected {sklearn.__version__}, got {metadata.sklearn_version}"
        )
    if metadata.features != expected:
        raise IncompatibleModelArtifactError(
            f"artifact features are incompatible: expected {expected}, got {metadata.features}"
        )
    if metadata.target != TARGET_COLUMN or metadata.forecast_horizon_minutes != 60:
        raise IncompatibleModelArtifactError("artifact prediction contract is incompatible")
    model = bundle["model"]
    supported = (
        HistoricalMeanBaseline,
        RandomForestRegressor,
        ExtraTreesRegressor,
        HistGradientBoostingRegressor,
    )
    if not isinstance(model, supported) or type(model).__name__ != metadata.algorithm:
        raise IncompatibleModelArtifactError("artifact model type is incompatible")
    if getattr(model, "n_features_in_", None) != len(expected):
        raise IncompatibleModelArtifactError("artifact model feature count is incompatible")
    return LoadedDemandModel(model=model, metadata=metadata)
