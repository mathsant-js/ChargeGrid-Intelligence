"""Run the Sprint 3 scenario through public HTTP endpoints only."""

import json
import os
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.environ.get("DEMO_API_URL", "http://localhost:8000/api/v1").rstrip("/")
PREFIX = "SPRINT3-DEMO"


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


def login(email: str, password: str) -> str:
    result = call("POST", "/auth/login", body={"email": email, "password": password})
    return result["access_token"]


def show(label: str, value: object) -> None:
    print(json.dumps({label: value}, ensure_ascii=False, indent=2))


def tick(admin: str, station_id: str, expected_count: int,
         expected_solar_kw: float) -> None:
    result = call("POST", "/simulation/ticks", admin)
    readings = call("GET", "/energy/history", params={"station_id": station_id})
    latest = [row for row in readings if row["timestamp"] == result["timestamp"]]
    if len(latest) != expected_count:
        raise RuntimeError(f"Expected {expected_count} readings, got {len(latest)}")
    totals = {key: round(sum(row[key] for row in latest), 4)
              for key in ("allocated_power_kw", "solar_power_kw", "grid_power_kw", "interval_energy_kwh")}
    if totals["grid_power_kw"] > 60.0001 or any(row["allocated_power_kw"] > 20.0001 for row in latest):
        raise RuntimeError("Energy limit violated")
    if (abs(totals["grid_power_kw"] - 60) > 0.01
            or abs(totals["solar_power_kw"] - expected_solar_kw) > 0.1
            or abs(totals["allocated_power_kw"] - (60 + expected_solar_kw)) > 0.1):
        raise RuntimeError(f"Unexpected power allocation: {totals}")
    show("tick", {"timestamp": result["timestamp"], "sessions": latest, "totals": totals})


def main() -> None:
    admin_password = os.environ.get("DEMO_ADMIN_PASSWORD")
    user_password = os.environ.get("DEMO_USER_PASSWORD")
    if not admin_password or not user_password:
        raise SystemExit("Set DEMO_ADMIN_PASSWORD and DEMO_USER_PASSWORD")
    admin = login("sprint3-admin@demo.invalid", admin_password)
    users = [login(f"sprint3-user-{i}@demo.invalid", user_password) for i in range(1, 5)]
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
    if call("GET", "/energy/history", params={"station_id": station["id"]}):
        raise RuntimeError("Use a fresh demo database; readings already exist")
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
    tick(admin, station["id"], 3, 0)
    fourth = call("POST", "/sessions/start", users[3],
                  {"vehicle_id": vehicles[3]["id"], "charger_id": chargers[3]["id"]})
    show("fourth_session", fourth)
    tick(admin, station["id"], 4, 0)
    updated = call("PATCH", f"/stations/{station['id']}", admin,
                   {"station_peak_solar_kw": 20})
    show("solar_configuration", updated)
    tick(admin, station["id"], 4, 20)
    show("solar_readings", call("GET", "/solar/history", params={"station_id": station["id"]}))
    show("alerts", call("GET", "/alerts", admin, params={"station_id": station["id"]}))
    show("admin_dashboard", call("GET", "/analytics/dashboard", admin,
                                  params={"station_id": station["id"]}))
    show("user_dashboard_before", call("GET", "/user/dashboard", users[3]))
    show("completed_session", call("POST", f"/sessions/{fourth['id']}/stop", users[3]))
    show("invoices", call("GET", "/billing/invoices", users[3]))
    show("sustainability", call("GET", "/analytics/sustainability", admin,
                                params={"station_id": station["id"]}))
    show("admin_dashboard_after", call("GET", "/analytics/dashboard", admin,
                                        params={"station_id": station["id"]}))
    show("user_dashboard_after", call("GET", "/user/dashboard", users[3]))


if __name__ == "__main__":
    main()
