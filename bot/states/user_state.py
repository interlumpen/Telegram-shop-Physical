from aiogram.filters.state import StatesGroup, State


class UserMgmtStates(StatesGroup):
    """FSM for user management flow."""
    waiting_user_id_for_check = State()
    waiting_user_bonus = State()


class ReferenceCodeStates(StatesGroup):
    """FSM for reference code validation flow."""
    waiting_reference_code = State()
    waiting_refcode_note = State()
    waiting_refcode_expires = State()
    waiting_refcode_max_uses = State()


class OrderStates(StatesGroup):
    """FSM for order placement flow."""
    waiting_delivery_address = State()
    waiting_phone_number = State()
    waiting_delivery_note = State()
    waiting_promo_code = State()  # For entering an optional promo code
    waiting_bonus_amount = State()  # For applying referral bonus to order
    waiting_payment_method = State()


class HelpStates(StatesGroup):
    """FSM for help/support flow."""
    waiting_help_message = State()


class CartStates(StatesGroup):
    """FSM for shopping cart checkout flow."""
    viewing_cart = State()
    waiting_quantity = State()


class SettingsFSM(StatesGroup):
    """FSM for bot settings management."""
    waiting_referral_percent = State()
    waiting_order_timeout = State()
    waiting_timezone = State()
