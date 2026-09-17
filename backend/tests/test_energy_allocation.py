"""Equal share allocation and solar priority for one station."""

from uuid import uuid4

import pytest

from app.services.energy_allocation import EqualSharePowerResolver, SessionPowerRequest


def resolve(
    requests: list[float], *, grid: float, solar: float = 0,
    charger: float = 100, vehicle: float = 100,
) -> list[tuple[float, float, float]]:
    sessions = [SessionPowerRequest(uuid4(), power, charger, vehicle) for power in requests]
    result = EqualSharePowerResolver().resolve(
        station_id=uuid4(), grid_limit_kw=grid,
        solar_available_kw=solar, sessions=sessions,
    )
    return [
        (result[item.session_id].allocated_power_kw,
         result[item.session_id].solar_power_kw,
         result[item.session_id].grid_power_kw)
        for item in sessions
    ]


def test_four_equal_requests_share_grid_limit() -> None:
    assert resolve([20] * 4, grid=60) == [(15, 0, 15)] * 4


def test_solar_adds_to_capacity_and_is_shared_proportionally() -> None:
    assert resolve([20] * 4, grid=60, solar=20) == [(20, 5, 15)] * 4
    assert resolve([10, 30], grid=60, solar=25) == [
        (10, 6.25, 3.75), (30, 18.75, 11.25)
    ]


def test_unequal_requests_redistribute_unused_share() -> None:
    result = resolve([5, 20, 20, 20], grid=45)
    assert [row[0] for row in result] == [5, 40 / 3, 40 / 3, 40 / 3]
    assert sum(row[2] for row in result) == pytest.approx(45)


def test_demand_below_capacity_and_individual_limits() -> None:
    assert resolve([5, 10], grid=60) == [(5, 0, 5), (10, 0, 10)]
    assert resolve([20], grid=60, charger=22, vehicle=11) == [(11, 0, 11)]


def test_zero_power_and_empty_sessions() -> None:
    assert resolve([0, 0], grid=0, solar=0) == [(0, 0, 0), (0, 0, 0)]
    assert resolve([20, 0], grid=0, solar=5) == [(5, 5, 0), (0, 0, 0)]
    assert resolve([], grid=60, solar=20) == []


@pytest.mark.parametrize("power", [-1, float("nan"), float("inf")])
def test_invalid_power_is_rejected(power: float) -> None:
    with pytest.raises(ValueError):
        resolve([power], grid=60)
    with pytest.raises(ValueError):
        resolve([20], grid=power)
