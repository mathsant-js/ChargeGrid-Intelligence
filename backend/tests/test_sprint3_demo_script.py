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
