"""Idempotent, explicitly named seed for the isolated Sprint 3 demo database."""

import os
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal
from app.models.billing import Tariff
from app.models.infrastructure import Charger, ChargerStatus, ChargingStation
from app.models.prediction import SystemConfiguration
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle

PREFIX = "SPRINT3-DEMO"
EMAILS = ["sprint3-admin@demo.invalid"] + [f"sprint3-user-{i}@demo.invalid" for i in range(1, 5)]
TARIFF = Decimal("0.8000")
EMISSION_FACTOR = 0.4


def seed(db: Session, admin_password: str, user_password: str) -> None:
    if len(admin_password) < 8 or len(user_password) < 8:
        raise ValueError("Demo passwords must each have at least 8 characters")
    for index, email in enumerate(EMAILS):
        role = UserRole.ADMIN if index == 0 else UserRole.USER
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(name=f"Sprint 3 Demo {'Admin' if index == 0 else f'User {index}'}",
                        email=email,
                        password_hash=hash_password(
                            admin_password if index == 0 else user_password
                        ),
                        role=role, is_active=True)
            db.add(user)
            db.flush()
        elif (user.role != role or not user.is_active or not verify_password(
            admin_password if index == 0 else user_password, user.password_hash
        )):
            raise ValueError(f"Demo account conflicts with existing user: {email}")
        if index:
            plate = f"S3D-{index:04d}"
            vehicle = db.scalar(select(Vehicle).where(Vehicle.license_plate == plate))
            if vehicle is None:
                db.add(Vehicle(user_id=user.id, name=f"Demo EV {index}", brand="Demo",
                               model="EV", license_plate=plate, max_charge_power_kw=20))
            elif vehicle.user_id != user.id or vehicle.max_charge_power_kw != 20:
                raise ValueError(f"Demo vehicle conflicts: {plate}")

    station = db.scalar(select(ChargingStation).where(ChargingStation.name == PREFIX))
    if station is None:
        station = ChargingStation(name=PREFIX, description="Sprint 3 simulated station",
                                  grid_limit_kw=60, station_peak_solar_kw=0, is_active=True)
        db.add(station)
        db.flush()
    elif (station.grid_limit_kw != 60 or station.station_peak_solar_kw not in (0, 20)
          or not station.is_active):
        raise ValueError("Demo station has conflicting configuration")
    for index in range(1, 5):
        code = f"{PREFIX}-CH-{index:02d}"
        charger = db.scalar(select(Charger).where(Charger.code == code))
        if charger is None:
            db.add(Charger(station_id=station.id, name=f"CH-{index:02d}", code=code,
                           max_power_kw=22, status=ChargerStatus.AVAILABLE, is_active=True))
        elif charger.station_id != station.id or charger.max_power_kw != 22:
            raise ValueError(f"Demo charger conflicts: {code}")

    tariff = db.scalar(select(Tariff).where(Tariff.name == PREFIX))
    if tariff is None:
        if db.scalar(select(Tariff).where(Tariff.is_active.is_(True))) is not None:
            raise ValueError("Another active tariff exists; use an isolated demo database")
        db.add(Tariff(name=PREFIX, price_per_kwh=TARIFF, currency="BRL", is_active=True,
                      valid_from=datetime(2020, 1, 1, tzinfo=UTC)))
    elif tariff.price_per_kwh != TARIFF or not tariff.is_active:
        raise ValueError("Demo tariff has conflicting configuration")
    config = db.scalar(select(SystemConfiguration).limit(1))
    if config is None:
        db.add(SystemConfiguration(simulation_speed=60,
                                   grid_emission_factor_kg_per_kwh=EMISSION_FACTOR,
                                   high_demand_threshold=0.85,
                                   medium_peak_threshold=0.7, high_peak_threshold=0.9))
    elif config.grid_emission_factor_kg_per_kwh != EMISSION_FACTOR or config.simulation_speed != 60:
        raise ValueError("Existing system configuration conflicts with demo")


def main() -> None:
    admin_password = os.environ.get("DEMO_ADMIN_PASSWORD")
    user_password = os.environ.get("DEMO_USER_PASSWORD")
    if not admin_password or not user_password:
        raise SystemExit("Set DEMO_ADMIN_PASSWORD and DEMO_USER_PASSWORD in the environment")
    with SessionLocal() as db, db.begin():
        seed(db, admin_password, user_password)
    print("Sprint 3 demo seed ready: 1 admin, 4 users, 4 vehicles, "
          "1 station, 4 chargers, 1 tariff, ESG config")


if __name__ == "__main__":
    main()
