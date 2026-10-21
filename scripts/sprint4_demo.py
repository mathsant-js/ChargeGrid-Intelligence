"""Run the automatic Sprint 4 Golden Path through public HTTP endpoints only."""

import json
import os
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.environ.get("DEMO_API_URL", "http://localhost:8000/api/v1").rstrip("/")
PREFIX = "SPRINT3-DEMO"
WAIT_TIMEOUT_SECONDS = float(os.environ.get("DEMO_AUTOMATIC_WAIT_TIMEOUT_SECONDS", "15"))
POLL_INTERVAL_SECONDS = 0.05


def call(method: str, path: str, token: str | None = None, body: dict | None = None,
         params: dict | None = None) -> object:
    url = BASE + path + ("?" + urlencode(params) if params else "")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, method=method, headers=headers,
                      data=json.dumps(body).encode() if body is not None else None)
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"{method} {path}: HTTP {exc.code} {exc.read().decode()}") from exc
    except (ConnectionError, TimeoutError, URLError) as exc:
        raise RuntimeError(f"{method} {path}: API connection failed at {BASE}") from exc


def require(condition: bool, stage: str, message: str) -> None:
    if not condition:
        raise RuntimeError(f"[{stage}] {message}")


def login(email: str, password: str) -> str:
    result = call("POST", "/auth/login", body={"email": email, "password": password})
    return result["access_token"]


def wait_for_readings(admin: str, station_id: str, timestamp: str,
                      count: int) -> list[dict]:
    """Wait for an automatic runner tick observed through the public history API."""
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        history = call("GET", "/energy/history", admin, params={"station_id": station_id})
        latest = [row for row in history if row["timestamp"] == timestamp]
        if len(latest) == count:
            return latest
        time.sleep(POLL_INTERVAL_SECONDS)
    raise RuntimeError(
        f"[automatic runner] expected {count} readings at {timestamp} within "
        f"{WAIT_TIMEOUT_SECONDS:g}s"
    )


def totals(readings: list[dict]) -> dict[str, float]:
    keys = ("requested_power_kw", "allocated_power_kw", "solar_power_kw",
            "grid_power_kw", "interval_energy_kwh")
    return {key: round(sum(float(row[key]) for row in readings), 4) for key in keys}


def validate_allocation(readings: list[dict], expected_solar: float,
                        expected_grid: float, expected_total: float) -> dict[str, float]:
    result = totals(readings)
    require(all(float(row["allocated_power_kw"]) >= 0 for row in readings),
            "energy invariants", "negative allocation")
    require(all(float(row["allocated_power_kw"]) <= float(row["requested_power_kw"]) + 1e-4
                for row in readings), "energy invariants", "request limit exceeded")
    require(result["grid_power_kw"] <= 60.0001, "energy invariants", "grid limit exceeded")
    require(abs(result["solar_power_kw"] - expected_solar) <= 0.01,
            "allocation", f"unexpected solar total: {result}")
    require(abs(result["grid_power_kw"] - expected_grid) <= 0.01,
            "allocation", f"unexpected grid total: {result}")
    require(abs(result["allocated_power_kw"] - expected_total) <= 0.01,
            "allocation", f"unexpected allocated total: {result}")
    return result


def main() -> None:
    admin_password = os.environ.get("DEMO_ADMIN_PASSWORD")
    user_password = os.environ.get("DEMO_USER_PASSWORD")
    if not admin_password or not user_password:
        raise SystemExit("Set DEMO_ADMIN_PASSWORD and DEMO_USER_PASSWORD")

    admin = login("sprint3-admin@demo.invalid", admin_password)
    users = [login(f"sprint3-user-{i}@demo.invalid", user_password) for i in range(1, 5)]
    station = next(row for row in call("GET", "/stations", admin)
                   if row["name"] == PREFIX)
    chargers = sorted(
        (row for row in call("GET", "/chargers", admin)
         if row["station_id"] == station["id"]), key=lambda row: row["code"]
    )
    require(len(chargers) == 4 and station["station_peak_solar_kw"] in (0, 20),
            "setup", "expected four chargers and a configurable demo station")
    if station["station_peak_solar_kw"] != 20:
        station = call("PATCH", f"/stations/{station['id']}", admin,
                       {"station_peak_solar_kw": 20})
    require(station["station_peak_solar_kw"] == 20, "setup",
            "could not configure the 20 kW solar peak through the public API")
    status = call("GET", "/simulation/status", admin)
    require(status["state"] == "STOPPED"
            and status["current_instant"] == "2026-09-18T11:58:00Z",
            "setup", f"unexpected simulation state: {status}")
    vehicles = [next(row for row in call("GET", "/vehicles", token)
                     if row["license_plate"] == f"S3D-{index:04d}")
                for index, token in enumerate(users, 1)]

    sessions = [call("POST", "/sessions/start", users[index], {
        "vehicle_id": vehicles[index]["id"], "charger_id": chargers[index]["id"]
    }) for index in range(3)]
    call("POST", "/simulation/start", admin)
    try:
        three = validate_allocation(
            wait_for_readings(admin, station["id"], "2026-09-18T11:58:00Z", 3),
            expected_solar=0, expected_grid=60, expected_total=60,
        )
        fourth = call("POST", "/sessions/start", users[3], {
            "vehicle_id": vehicles[3]["id"], "charger_id": chargers[3]["id"]
        })
        sessions.append(fourth)
        equal_share = validate_allocation(
            wait_for_readings(admin, station["id"], "2026-09-18T11:59:00Z", 4),
            expected_solar=0, expected_grid=60, expected_total=60,
        )
        solar_priority = validate_allocation(
            wait_for_readings(admin, station["id"], "2026-09-18T12:02:00Z", 4),
            expected_solar=20, expected_grid=60, expected_total=80,
        )
    finally:
        call("POST", "/simulation/stop", admin)

    prediction = call("POST", "/predictions/demand/run", admin,
                      {"station_id": station["id"]})
    alerts = call("GET", "/alerts", admin, params={"station_id": station["id"]})
    alert_types = sorted({row["type"] for row in alerts})
    require({"HIGH_DEMAND", "HIGH_SOLAR_AVAILABILITY", "PEAK_RISK"} <= set(alert_types),
            "alerts", f"missing expected alerts: {alert_types}")
    completed = call("POST", f"/sessions/{fourth['id']}/stop", users[3])
    invoice = call("GET", "/billing/invoices", users[3])[0]
    require(invoice["status"] == "CLOSED"
            and Decimal(invoice["total"]) == Decimal(completed["total_cost"]),
            "billing", "closed invoice does not match the completed session")
    sustainability = call("GET", "/analytics/sustainability", admin,
                          params={"station_id": station["id"]})
    require(sustainability["solar_energy_kwh"] > 0
            and sustainability["avoided_co2_kg"] > 0,
            "ESG", f"unexpected sustainability result: {sustainability}")

    summary = {
        "scenario": "Sprint 4 automatic Golden Path",
        "data_source": "synthetic telemetry replay",
        "automatic_ticks": True,
        "stages": {
            "three_sessions": three,
            "four_sessions_equal_share": equal_share,
            "solar_priority": solar_priority,
        },
        "violations": 0,
        "energy_total_kwh": sustainability["energy_consumed_kwh"],
        "solar_share_percent": sustainability["solar_percentage"],
        "avoided_co2_kg": sustainability["avoided_co2_kg"],
        "estimated_solar_savings_brl": sustainability["estimated_solar_savings"],
        "completed_session_energy_kwh": completed["energy_consumed_kwh"],
        "invoice_total_brl": invoice["total"],
        "predicted_demand_kw": prediction["predicted_demand_kw"],
        "peak_risk": prediction["risk_level"],
        "recommendation": prediction["recommendation"],
        "alerts": alert_types,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
