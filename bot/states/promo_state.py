from aiogram.filters.state import StatesGroup, State


class PromoFSM(StatesGroup):
    """FSM for admin promo-code creation."""
    waiting_code = State()
    waiting_type = State()
    waiting_value = State()
    waiting_max_uses = State()
    waiting_expiry_hours = State()
