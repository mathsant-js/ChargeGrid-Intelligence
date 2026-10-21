import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def load_demo_script() -> ModuleType:
    path = Path(__file__).parents[2] / "scripts" / "sprint4_demo.py"
    spec = importlib.util.spec_from_file_location("sprint4_demo", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reading(timestamp: str, allocated: float, solar: float, grid: float) -> dict:
    return {
        "timestamp": timestamp,
        "requested_power_kw": 20,
        "allocated_power_kw": allocated,
        "solar_power_kw": solar,
        "grid_power_kw": grid,
        "interval_energy_kwh": allocated,
    }


def test_wait_for_readings_observes_history_without_manual_ticks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = load_demo_script()
    calls: list[tuple[str, str]] = []
    responses = iter([[], [reading("2026-09-18T11:58:00Z", 20, 0, 20)]])
    monkeypatch.setattr(demo, "call", lambda method, path, *args, **kwargs: (
        calls.append((method, path)), next(responses)
    )[1])
    monkeypatch.setattr(demo.time, "sleep", lambda _: None)

    result = demo.wait_for_readings(
        "admin", "station", "2026-09-18T11:58:00Z", 1
    )

    assert len(result) == 1
    assert calls == [("GET", "/energy/history"), ("GET", "/energy/history")]
    assert ("POST", "/simulation/ticks") not in calls


def test_validate_allocation_enforces_grid_and_request_limits() -> None:
    demo = load_demo_script()
    rows = [reading("2026-09-18T12:02:00Z", 20, 5, 15) for _ in range(4)]
    assert demo.validate_allocation(rows, 20, 60, 80)["allocated_power_kw"] == 80

    rows[0]["allocated_power_kw"] = 21
    with pytest.raises(RuntimeError, match="request limit exceeded"):
        demo.validate_allocation(rows, 20, 60, 80)


def test_automatic_demo_uses_start_and_stop_but_never_manual_tick() -> None:
    source = (Path(__file__).parents[2] / "scripts" / "sprint4_demo.py").read_text()
    assert 'call("POST", "/simulation/start"' in source
    assert 'call("POST", "/simulation/stop"' in source
    assert 'call("POST", "/simulation/ticks"' not in source
