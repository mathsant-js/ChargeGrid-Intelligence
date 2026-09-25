from pathlib import Path

import joblib
import pytest
import sklearn

from app.ml.baseline import evaluate_hour_weekday_baseline
from app.ml.dataset import DatasetConfig, DemandDatasetRow, generate_dataset
from app.ml.training import (
    BASELINE_NAME,
    MODEL_FEATURES,
    IncompatibleModelArtifactError,
    ModelArtifactNotFoundError,
    load_model_artifact,
    train_and_evaluate,
)


@pytest.fixture(scope="module")
def dataset() -> list[DemandDatasetRow]:
    return generate_dataset(DatasetConfig(days=10, seed=21))


def _train(dataset: list[DemandDatasetRow], artifact_path: Path):
    baseline = evaluate_hour_weekday_baseline(dataset, test_fraction=0.2)
    result = train_and_evaluate(
        dataset,
        baseline_metrics=baseline.metrics,
        artifact_path=artifact_path,
        test_fraction=0.2,
        random_state=21,
        n_estimators=20,
    )
    return baseline, result


def test_training_uses_same_strict_temporal_split_as_baseline(
    dataset: list[DemandDatasetRow], tmp_path: Path
) -> None:
    baseline, result = _train(dataset, tmp_path / "model.joblib")

    assert result.metadata.training_period.start == baseline.train_start
    assert result.metadata.training_period.end == baseline.train_end
    assert result.metadata.test_period.start == baseline.test_start
    assert result.metadata.test_period.end == baseline.test_end
    assert result.metadata.training_period.end < result.metadata.test_period.start


def test_training_reports_required_metrics_and_baseline_comparison(
    dataset: list[DemandDatasetRow], tmp_path: Path
) -> None:
    baseline, result = _train(dataset, tmp_path / "model.joblib")

    assert "RandomForestRegressor" in result.comparison.candidates
    assert len(result.comparison.candidates) == 4  # baseline + at most three classical models
    assert result.metadata.sklearn_version == sklearn.__version__
    assert result.metadata.metrics.mae >= 0
    assert result.metadata.metrics.rmse >= 0
    assert result.metadata.metrics.r2 == pytest.approx(result.metadata.metrics.r2)
    assert result.comparison.candidates[BASELINE_NAME] == baseline.metrics
    assert result.metadata.metrics == result.comparison.candidates[result.comparison.winner]
    assert all(
        metrics.mae >= 0 and metrics.rmse >= 0 for metrics in result.comparison.candidates.values()
    )
    assert result.comparison.selection_metric == "rmse"
    assert result.comparison.winner == min(
        result.comparison.candidates,
        key=lambda name: result.comparison.candidates[name].rmse,
    )


def test_model_is_persisted_reloaded_and_predicts(
    dataset: list[DemandDatasetRow], tmp_path: Path
) -> None:
    artifact_path = tmp_path / "model.joblib"
    _, result = _train(dataset, artifact_path)

    loaded = load_model_artifact(artifact_path)
    predictions = loaded.predict(dataset[-3:])

    assert artifact_path.is_file()
    assert loaded.metadata == result.metadata
    assert len(predictions) == 3
    assert all(prediction >= 0 for prediction in predictions)


def test_training_is_deterministic(dataset: list[DemandDatasetRow], tmp_path: Path) -> None:
    _, first = _train(dataset, tmp_path / "first.joblib")
    _, second = _train(dataset, tmp_path / "second.joblib")
    assert first.comparison == second.comparison
    assert load_model_artifact(tmp_path / "first.joblib").predict(dataset[-10:]) == pytest.approx(
        load_model_artifact(tmp_path / "second.joblib").predict(dataset[-10:])
    )


def test_baseline_can_win_and_is_persisted(
    dataset: list[DemandDatasetRow], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.ml.training._candidate_models", lambda *_: {})
    baseline, result = _train(dataset, tmp_path / "baseline.joblib")
    loaded = load_model_artifact(tmp_path / "baseline.joblib")
    assert result.comparison.baseline_won is True
    assert result.comparison.winner == BASELINE_NAME
    assert result.metadata.metrics == baseline.metrics
    assert len(loaded.predict(dataset[-2:])) == 2


def test_loading_missing_artifact_fails_explicitly(tmp_path: Path) -> None:
    with pytest.raises(ModelArtifactNotFoundError, match="not found"):
        load_model_artifact(tmp_path / "missing.joblib")


def test_loading_rejects_incompatible_expected_features(
    dataset: list[DemandDatasetRow], tmp_path: Path
) -> None:
    artifact_path = tmp_path / "model.joblib"
    _train(dataset, artifact_path)

    with pytest.raises(IncompatibleModelArtifactError, match="features are incompatible"):
        load_model_artifact(artifact_path, expected_features=(*MODEL_FEATURES, "grid_power_kw"))


def test_loading_rejects_tampered_feature_metadata(
    dataset: list[DemandDatasetRow], tmp_path: Path
) -> None:
    artifact_path = tmp_path / "model.joblib"
    _train(dataset, artifact_path)
    bundle = joblib.load(artifact_path)
    bundle["metadata"]["features"] = (*MODEL_FEATURES[:-1], "grid_power_kw")
    joblib.dump(bundle, artifact_path)

    with pytest.raises(IncompatibleModelArtifactError, match="features are incompatible"):
        load_model_artifact(artifact_path)


def test_loading_rejects_incompatible_sklearn_version(
    dataset: list[DemandDatasetRow], tmp_path: Path
) -> None:
    artifact_path = tmp_path / "model.joblib"
    _train(dataset, artifact_path)
    bundle = joblib.load(artifact_path)
    bundle["metadata"]["sklearn_version"] = "0.0.0"
    joblib.dump(bundle, artifact_path)

    with pytest.raises(IncompatibleModelArtifactError, match="scikit-learn version"):
        load_model_artifact(artifact_path)


def test_loading_rejects_incompatible_forecast_horizon(
    dataset: list[DemandDatasetRow], tmp_path: Path
) -> None:
    artifact_path = tmp_path / "model.joblib"
    _train(dataset, artifact_path)
    bundle = joblib.load(artifact_path)
    bundle["metadata"]["forecast_horizon_minutes"] = 30
    joblib.dump(bundle, artifact_path)

    with pytest.raises(IncompatibleModelArtifactError, match="prediction contract"):
        load_model_artifact(artifact_path)
