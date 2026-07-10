from decimal import Decimal
from typing import Union

from bot.config import EnvKeys

Number = Union[int, float, str, Decimal]


def format_price(amount: Number) -> str:
    """Format a monetary amount with the configured currency.

    Use everywhere a price is shown to users so a physical (RUB by default) shop
    never renders a hardcoded "$". Example: format_price(100) -> "100 RUB".
    """
    return f"{amount} {EnvKeys.PAY_CURRENCY}"
