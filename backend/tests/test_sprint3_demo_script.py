import importlib.util
from pathlib import Path
from types import ModuleType
from urllib.error import URLError

import pytest


def load_demo_script() -> ModuleType:
    path = Path(__file__).parents[2] / "scripts" / "sprint3_demo.py"
    spec = importlib.util.spec_from_file_location("sprint3_demo", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HealthyResponse:
    status = 200

    def __enter__(self) -> "HealthyResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_wait_for_api_retries_transient_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = load_demo_script()
    attempts = iter([URLError("starting"), HealthyResponse()])
    monotonic_values = iter([0.0, 0.0, 0.1])

    def open_api(*args: object, **kwargs: object) -> HealthyResponse:
        result = next(attempts)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(demo, "urlopen", open_api)
    monkeypatch.setattr(demo.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(demo.time, "sleep", lambda _: None)

    demo.wait_for_api(timeout_seconds=1)


def test_wait_for_api_reports_backend_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    demo = load_demo_script()
    monotonic_values = iter([0.0, 0.0, 1.0])

    monkeypatch.setattr(demo, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(
        URLError("unavailable")
    ))
    monkeypatch.setattr(demo.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(demo.time, "sleep", lambda _: None)

    with pytest.raises(RuntimeError, match=r"docker compose logs backend"):
        demo.wait_for_api(timeout_seconds=0.5)


def test_tick_authenticates_energy_history(monkeypatch: pytest.MonkeyPatch) -> None:
    demo = load_demo_script()
    calls: list[tuple[str, str, str | None]] = []

    def fake_call(
        method: str,
        path: str,
        token: str | None = None,
        body: dict | None = None,
        params: dict | None = None,
    ) -> object:
        calls.append((method, path, token))
        if path == "/simulation/ticks":
            return {"timestamp": "2026-09-18T11:58:00Z"}
        return [
            {
                "timestamp": "2026-09-18T11:58:00Z",
                "allocated_power_kw": 20,
                "solar_power_kw": 0,
                "grid_power_kw": 20,
                "interval_energy_kwh": 1 / 3,
            }
            for _ in range(3)
        ]

    monkeypatch.setattr(demo, "call", fake_call)
    monkeypatch.setattr(demo, "show", lambda *_: None)

    demo.tick("admin-token", "station-id", expected_count=3, expected_solar_kw=0)

    assert ("GET", "/energy/history", "admin-token") in calls


def test_complete_demo_runs_advisory_prediction_with_documented_thresholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = load_demo_script()
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "admin-secret")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "user-secret")
    monkeypatch.setattr(demo, "wait_for_api", lambda: None)
    monkeypatch.setattr(demo, "login", lambda email, password: f"token:{email}")
    monkeypatch.setattr(demo, "show", lambda *_: None)
    monkeypatch.setattr(demo, "tick", lambda *args, **kwargs: None)
    calls: list[tuple[str, str, dict | None]] = []
    history = [{"timestamp": "2026-09-11T12:01:00Z", "allocated_power_kw": 20}]
    session_number = 0

    def fake_call(
        method: str,
        path: str,
        token: str | None = None,
        body: dict | None = None,
        params: dict | None = None,
    ) -> object:
        nonlocal session_number
        calls.append((method, path, body))
        if path == "/stations":
            return [{"id": "station", "name": demo.PREFIX, "station_peak_solar_kw": 0}]
        if path == "/chargers":
            return [
                {"id": f"charger-{i}", "station_id": "station", "code": f"CH-{i}"}
                for i in range(1, 5)
            ]
        if path == "/simulation/status":
            return {"state": "STOPPED", "current_instant": "2026-09-18T11:58:00Z"}
        if path == "/vehicles":
            return [
                {"id": f"vehicle-{i}", "license_plate": f"S3D-{i:04d}"}
                for i in range(1, 5)
            ]
        if path == "/sessions/start":
            session_number += 1
            return {"id": f"session-{session_number}"}
        if path == "/system-configuration":
            return {"medium_peak_threshold": 0.7, "high_peak_threshold": 0.9}
        if path == "/predictions/demand/run":
            return {
                "predicted_demand_kw": 73.9,
                "capacity_kw": 80,
                "prediction_horizon_minutes": 60,
                "risk_level": "HIGH",
                "recommendation": "deterministic",
            }
        if path == "/energy/history":
            return history
        if method == "PATCH" and path == "/stations/station":
            return {"station_peak_solar_kw": 20}
        return []

    monkeypatch.setattr(demo, "call", fake_call)

    demo.main()

    assert ("POST", "/predictions/demand/run", {"station_id": "station"}) in calls
    assert not any(
        method == "PATCH" and path == "/system-configuration"
        for method, path, _ in calls
    )
