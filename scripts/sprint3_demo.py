"""Run the Sprint 3 scenario through public HTTP endpoints only."""

import json
import os
import time
from datetime import datetime
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.environ.get("DEMO_API_URL", "http://localhost:8000/api/v1").rstrip("/")
FRONTEND = os.environ.get("DEMO_FRONTEND_URL", "http://localhost:5173").rstrip("/")
PREFIX = "SPRINT3-DEMO"
API_READY_TIMEOUT_SECONDS = 30


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
        raise RuntimeError(
            f"{method} {path}: API connection failed at {BASE}. "
            "Check `docker compose ps` and `docker compose logs backend`."
        ) from exc


def wait_for_api(timeout_seconds: float = API_READY_TIMEOUT_SECONDS) -> None:
    """Wait for startup without retrying any operation that changes demo state."""
    deadline = time.monotonic() + timeout_seconds
    last_error: OSError | None = None
    health_url = BASE + "/health"
    while time.monotonic() < deadline:
        try:
            with urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except (ConnectionError, TimeoutError, URLError) as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(
        f"API did not become ready at {health_url} within {timeout_seconds:g}s. "
        "Check `docker compose ps` and `docker compose logs backend`."
    ) from last_error


def login(email: str, password: str) -> str:
    result = call("POST", "/auth/login", body={"email": email, "password": password})
    return result["access_token"]


def show(label: str, value: object) -> None:
    print(json.dumps({label: value}, ensure_ascii=False, indent=2))


def require(condition: bool, stage: str, message: str) -> None:
    if not condition:
        raise RuntimeError(f"[{stage}] {message}")


def tick(admin: str, station_id: str, expected_count: int,
         expected_solar_kw: float, expected_session_kw: float) -> list[dict]:
    result = call("POST", "/simulation/ticks", admin)
    readings = call("GET", "/energy/history", admin, params={"station_id": station_id})
    latest = [row for row in readings if row["timestamp"] == result["timestamp"]]
    require(len(latest) == expected_count, "simulation tick",
            f"expected {expected_count} readings, got {len(latest)}")
    total_keys = (
        "allocated_power_kw",
        "solar_power_kw",
        "grid_power_kw",
        "interval_energy_kwh",
    )
    totals = {key: round(sum(row[key] for row in latest), 4) for key in total_keys}
    allocation_exceeded = any(row["allocated_power_kw"] > 20.0001 for row in latest)
    require(not allocation_exceeded and totals["grid_power_kw"] <= 60.0001,
            "energy limits", f"physical limit violated: {totals}")
    require(all(abs(row["allocated_power_kw"] - expected_session_kw) <= 0.01
                for row in latest), "power allocation",
            f"expected {expected_session_kw} kW per session")
    require(abs(totals["grid_power_kw"] - 60) <= 0.01
            and abs(totals["solar_power_kw"] - expected_solar_kw) <= 0.1
            and abs(totals["allocated_power_kw"] - (60 + expected_solar_kw)) <= 0.1,
            "power allocation", f"unexpected totals: {totals}")
    require(all(abs(row["interval_energy_kwh"] - row["solar_energy_kwh"]
                        - row["grid_energy_kwh"]) <= 0.0001 for row in latest),
            "energy conservation", "interval energy differs from solar plus grid energy")
    show("tick", {"timestamp": result["timestamp"], "sessions": latest, "totals": totals})
    return latest


def validate_web_surfaces() -> None:
    try:
        with urlopen(BASE.removesuffix("/api/v1") + "/openapi.json", timeout=10) as response:
            schema = json.load(response)
        require("/api/v1/health" in schema.get("paths", {}), "OpenAPI",
                "generated schema does not contain the health endpoint")
        with urlopen(FRONTEND, timeout=10) as response:
            html = response.read().decode(errors="replace")
        require(response.status == 200 and "<div id=\"root\"></div>" in html,
                "frontend", f"unexpected response from {FRONTEND}")
    except (ConnectionError, TimeoutError, URLError) as exc:
        raise RuntimeError(f"[web surfaces] failed to access OpenAPI or frontend: {exc}") from exc


def main() -> None:
    admin_password = os.environ.get("DEMO_ADMIN_PASSWORD")
    user_password = os.environ.get("DEMO_USER_PASSWORD")
    if not admin_password or not user_password:
        raise SystemExit("Set DEMO_ADMIN_PASSWORD and DEMO_USER_PASSWORD")
    wait_for_api()
    health = call("GET", "/health")
    require(health == {"status": "ok"}, "health", f"unexpected response: {health}")
    admin = login("sprint3-admin@demo.invalid", admin_password)
    users = [login(f"sprint3-user-{i}@demo.invalid", user_password) for i in range(1, 5)]
    require(call("GET", "/auth/me", admin)["role"] == "ADMIN", "ADMIN authentication",
            "authenticated account does not have ADMIN role")
    require(all(call("GET", "/auth/me", token)["role"] == "USER" for token in users),
            "USER authentication", "one or more demo accounts do not have USER role")
    stations = call("GET", "/stations", admin)
    station = next(row for row in stations if row["name"] == PREFIX)
    chargers = call("GET", "/chargers", admin)
    chargers = sorted((row for row in chargers if row["station_id"] == station["id"]),
                      key=lambda row: row["code"])
    if len(chargers) != 4 or station["station_peak_solar_kw"] != 0:
        raise RuntimeError("Use a fresh seeded demo database with solar peak 0")
    status = call("GET", "/simulation/status", admin)
    instant = datetime.fromisoformat(status["current_instant"].replace("Z", "+00:00"))
    if status["state"] != "STOPPED" or instant.utcoffset().total_seconds() != 0:
        raise RuntimeError("Expected a stopped UTC simulation clock")
    hour, minute = instant.hour, instant.minute
    if hour != 11 or not 55 <= minute <= 59:
        raise RuntimeError("Set DEMO_SIMULATION_START_UTC near 11:58 UTC and restart the API")
    existing_readings = call(
        "GET", "/energy/history", admin, params={"station_id": station["id"]}
    )
    if any(datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) >= instant
           for row in existing_readings):
        raise RuntimeError("Use a freshly prepared demo database; scenario readings exist")
    vehicles = [next(row for row in call("GET", "/vehicles", user)
                     if row["license_plate"] == f"S3D-{i:04d}")
                for i, user in enumerate(users, 1)]
    sessions = []
    for i in range(3):
        session = call("POST", "/sessions/start", users[i],
                       {"vehicle_id": vehicles[i]["id"], "charger_id": chargers[i]["id"]})
        sessions.append(session)
    show("three_sessions", sessions)
    call("POST", "/simulation/start", admin)
    first_tick = tick(admin, station["id"], 3, 0, 20)
    require(all(row["requested_power_kw"] == 20 for row in first_tick),
            "three sessions", "the first three sessions did not request 20 kW")
    fourth = call("POST", "/sessions/start", users[3],
                  {"vehicle_id": vehicles[3]["id"], "charger_id": chargers[3]["id"]})
    show("fourth_session", fourth)
    tick(admin, station["id"], 4, 0, 15)
    updated = call("PATCH", f"/stations/{station['id']}", admin,
                   {"station_peak_solar_kw": 20})
    show("solar_configuration", updated)
    tick(admin, station["id"], 4, 20, 20)
    call("POST", "/simulation/stop", admin)
    show(
        "solar_readings",
        call("GET", "/solar/history", admin, params={"station_id": station["id"]}),
    )
    configuration = call("GET", "/system-configuration", admin)
    if (configuration["medium_peak_threshold"], configuration["high_peak_threshold"]) != (
        0.7,
        0.9,
    ):
        raise RuntimeError("Official demo requires the documented 0.70/0.90 risk thresholds")
    before_prediction = call(
        "GET", "/energy/history", admin, params={"station_id": station["id"]}
    )
    prediction = call(
        "POST", "/predictions/demand/run", admin, {"station_id": station["id"]}
    )
    after_prediction = call(
        "GET", "/energy/history", admin, params={"station_id": station["id"]}
    )
    if before_prediction != after_prediction:
        raise RuntimeError("Advisory prediction changed persisted energy allocation")
    if (
        prediction["risk_level"] != "HIGH"
        or prediction["prediction_horizon_minutes"] != 60
        or abs(prediction["capacity_kw"] - 80) > 0.1
    ):
        raise RuntimeError(f"Expected reproducible HIGH prediction, got {prediction}")
    show("demand_prediction", prediction)
    alerts = call("GET", "/alerts", admin, params={"station_id": station["id"]})
    alert_types = {item["type"] for item in alerts}
    require({"HIGH_DEMAND", "HIGH_SOLAR_AVAILABILITY", "PEAK_RISK"} <= alert_types,
            "alerts", f"missing required alert types; received {sorted(alert_types)}")
    show("alerts", alerts)
    dashboard_before = call("GET", "/analytics/dashboard", admin,
                            params={"station_id": station["id"]})
    require(dashboard_before["session_count"] - dashboard_before["completed_session_count"] == 4
            and dashboard_before["energy_consumed_kwh"] > 0,
            "admin dashboard", f"unexpected pre-close dashboard: {dashboard_before}")
    show("admin_dashboard", dashboard_before)
    show("user_dashboard_before", call("GET", "/user/dashboard", users[3]))
    completed = call("POST", f"/sessions/{fourth['id']}/stop", users[3])
    require(completed["status"] == "COMPLETED", "session close",
            f"unexpected status: {completed['status']}")
    charger = call("GET", f"/chargers/{chargers[3]['id']}", admin)
    require(charger["status"] == "AVAILABLE", "charger release",
            f"unexpected charger status: {charger['status']}")
    invoices = call("GET", "/billing/invoices", users[3])
    require(len(invoices) == 1 and invoices[0]["status"] == "CLOSED", "invoice close",
            f"unexpected invoices: {invoices}")
    invoice = invoices[0]
    require(invoice["subtotal"] == invoice["total"] == completed["total_cost"],
            "billing consistency", "invoice and completed session totals differ")
    require(Decimal(invoice["total"]) == Decimal("0.47"), "billing amount",
            f"expected BRL 0.47 for the deterministic scenario, got {invoice['total']}")
    require(abs(float(invoice["energy_kwh"]) - completed["energy_consumed_kwh"]) <= 0.0001,
            "billing energy", "invoice energy differs from completed session")
    sustainability = call("GET", "/analytics/sustainability", admin,
                          params={"station_id": station["id"]})
    require(sustainability["energy_consumed_kwh"] > 0
            and sustainability["solar_energy_kwh"] > 0
            and sustainability["avoided_co2_kg"] > 0,
            "ESG dashboard", f"indicators were not updated: {sustainability}")
    dashboard_after = call("GET", "/analytics/dashboard", admin,
                           params={"station_id": station["id"]})
    require(dashboard_after["session_count"] == dashboard_before["session_count"]
            and dashboard_after["completed_session_count"]
            == dashboard_before["completed_session_count"] + 1
            and dashboard_after["billed_total"] == invoice["total"],
            "admin dashboard after close", f"dashboard was not updated: {dashboard_after}")
    user_after = call("GET", "/user/dashboard", users[3])
    require(user_after["current_session"] is None
            and user_after["invoices"][0]["id"] == invoice["id"],
            "user dashboard after close", f"dashboard was not updated: {user_after}")
    show("completed_session", completed)
    show("invoices", invoices)
    show("sustainability", sustainability)
    show("admin_dashboard_after", dashboard_after)
    show("user_dashboard_after", user_after)
    validate_web_surfaces()


if __name__ == "__main__":
    main()
