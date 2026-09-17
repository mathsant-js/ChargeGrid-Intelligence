from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def calculate_pay_per_use_total(energy_kwh: float, tariff_per_kwh: Decimal) -> Decimal:
    """Price accumulated energy at the tariff captured when the session started."""
    return (Decimal(str(energy_kwh)) * tariff_per_kwh).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
