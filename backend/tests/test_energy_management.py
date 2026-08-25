import pytest

from app.services.energy_management import PowerRequest, allocate_power, interval_energy_kwh


def request(session_id: str, power: float = 20) -> PowerRequest:
    return PowerRequest(session_id, power, power, power)


def test_equal_share_protects_grid_limit() -> None:
    result = allocate_power(
        [request("A"), request("B"), request("C"), request("D")],
        grid_limit_kw=60,
        solar_available_kw=0,
    )

    assert [item.allocated_power_kw for item in result.allocations] == [15, 15, 15, 15]
    assert result.total_requested_kw == 80
    assert result.grid_used_kw == 60


def test_allocation_redistributes_spare_capacity_and_prioritizes_solar() -> None:
    result = allocate_power(
        [request("A", 5), request("B", 30), request("C", 30)],
        grid_limit_kw=25,
        solar_available_kw=20,
    )

    assert [item.allocated_power_kw for item in result.allocations] == pytest.approx([5, 20, 20])
    assert result.solar_used_kw == 20
    assert result.grid_used_kw == 25
    assert sum(item.solar_power_kw for item in result.allocations) == pytest.approx(20)


def test_individual_equipment_limits_are_never_exceeded() -> None:
    limited = PowerRequest("A", 50, 22, 11)
    result = allocate_power([limited], grid_limit_kw=60, solar_available_kw=20)

    assert result.allocations[0].requested_power_kw == 11
    assert result.allocations[0].allocated_power_kw == 11


def test_interval_energy_uses_minutes() -> None:
    assert interval_energy_kwh(15, 5) == pytest.approx(1.25)
