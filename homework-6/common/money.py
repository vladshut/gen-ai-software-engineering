"""Decimal money helpers: parsing, FX conversion, fee application.

Pattern applied from context7 `/python/cpython` decimal docs:
  - quantize to two places via TWOPLACES = Decimal(10) ** -2
  - ROUND_HALF_UP rounding mode ("round to nearest, ties away from zero")
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .constants import (
    ALLOW_NEGATIVE_FOR_REFUND,
    FX_RATES_TO_USD,
    MAX_DECIMAL_PLACES,
    MIN_SETTLEMENT_FEE,
    SETTLEMENT_FEE_RATE,
)

# Decimal(10) ** -2 == Decimal('0.01'); the quantize target for cents.
TWOPLACES = Decimal(10) ** -MAX_DECIMAL_PLACES


class AmountError(ValueError):
    """Raised when an amount string violates the frozen amount rule."""


def parse_amount(raw: str | int | float | Decimal) -> Decimal:
    """Parse a raw amount into a validated Decimal.

    Rules (frozen contract):
      * must parse as a Decimal
      * must have <= MAX_DECIMAL_PLACES decimal places
      * must be > 0 unless ALLOW_NEGATIVE_FOR_REFUND is True (then != 0)

    Floats are routed through str() so e.g. 0.1 does not pick up binary noise.
    """
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise AmountError(f"unparseable amount: {raw!r}") from exc

    if value != value:  # NaN guard
        raise AmountError(f"amount is NaN: {raw!r}")

    exponent = value.as_tuple().exponent
    # exponent is an int for finite Decimals; negative means decimal places.
    if isinstance(exponent, int) and -exponent > MAX_DECIMAL_PLACES:
        raise AmountError(
            f"amount has more than {MAX_DECIMAL_PLACES} decimal places: {raw!r}"
        )

    if ALLOW_NEGATIVE_FOR_REFUND:
        if value == 0:
            raise AmountError("amount must be non-zero")
    else:
        if value <= 0:
            raise AmountError(f"amount must be > 0: {raw!r}")

    return value


def to_usd(amount: Decimal, currency: str) -> Decimal:
    """Convert an amount in `currency` to USD using static documented rates.

    Result is quantized to two places with ROUND_HALF_UP.
    """
    if currency not in FX_RATES_TO_USD:
        raise AmountError(f"no FX rate for currency: {currency!r}")
    converted = amount * FX_RATES_TO_USD[currency]
    return converted.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def apply_fee(usd_amount: Decimal) -> Decimal:
    """Return the settlement fee for a USD amount.

    0.1% of the amount, ROUND_HALF_UP to cents, floored at MIN_SETTLEMENT_FEE.
    """
    fee = (usd_amount * SETTLEMENT_FEE_RATE).quantize(
        TWOPLACES, rounding=ROUND_HALF_UP
    )
    return max(fee, MIN_SETTLEMENT_FEE)


def net_after_fee(usd_amount: Decimal) -> Decimal:
    """USD amount minus the settlement fee, quantized to cents."""
    return (usd_amount - apply_fee(usd_amount)).quantize(
        TWOPLACES, rounding=ROUND_HALF_UP
    )
