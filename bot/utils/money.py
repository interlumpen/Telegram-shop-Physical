from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Tuple, Union

from bot.config import EnvKeys

Number = Union[int, float, str, Decimal]


def format_price(amount: Number) -> str:
    """Format a monetary amount with the configured currency.

    Use everywhere a price is shown to users so a physical (RUB by default) shop
    never renders a hardcoded "$". Example: format_price(100) -> "100 RUB".
    """
    return f"{amount} {EnvKeys.PAY_CURRENCY}"


def _q2(value: Decimal) -> Decimal:
    """Round to 2 decimal places (money)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_sale_percent(percent: Number) -> str:
    """Format a discount percent without trailing zeros: 20.00 -> "20", 15.50 -> "15.5"."""
    value = Decimal(str(percent)).normalize()
    # normalize() can yield exponent form (e.g. 2E+1); 'f' forces plain notation.
    return f"{value:f}"


def as_datetime(value) -> Optional[datetime]:
    """Coerce a value to an aware UTC datetime, or None.

    Cached item dicts come back from Redis as JSON, so a stored datetime becomes
    an ISO string; ORM reads give a real datetime. Handle both.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def effective_price(
    price: Number,
    sale_percent: Optional[Number] = None,
    sale_until: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> Tuple[Decimal, bool, Decimal]:
    """Compute the current price of a product, applying an active time-limited sale.

    Args:
        price: the product's base price.
        sale_percent: sale discount percentage (0..100), or None.
        sale_until: UTC datetime the sale is valid until, or None.
        now: override for "current time" (testing); defaults to now(UTC).

    Returns:
        (final_price, on_sale, original_price) — all Decimals rounded to 2dp.
        When there is no active sale, final == original and on_sale is False.
    """
    original = _q2(Decimal(str(price)))

    if sale_percent is None or sale_until is None:
        return original, False, original

    try:
        percent = Decimal(str(sale_percent))
    except (InvalidOperation, ValueError):
        return original, False, original
    if percent <= 0:
        return original, False, original
    # Clamp to a sane range so a bad value can't make the price negative/free.
    percent = min(percent, Decimal("100"))

    # sale_until may be a datetime (ORM) or an ISO string (from JSON cache).
    until = as_datetime(sale_until)
    if until is None:
        return original, False, original

    current = now or datetime.now(timezone.utc)
    if until <= current:
        return original, False, original

    final = _q2(original * (Decimal("100") - percent) / Decimal("100"))
    if final < 0:
        final = Decimal("0.00")
    return final, True, original
