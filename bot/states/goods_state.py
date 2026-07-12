from aiogram.filters.state import StatesGroup, State


class GoodsFSM(StatesGroup):
    """FSM for position (goods) and items management scenarios."""
    waiting_item_name_delete = State()
    waiting_item_name_show = State()
    # Time-limited sale management
    waiting_sale_item_name = State()
    waiting_sale_percent = State()
    waiting_sale_days = State()


class AddItemFSM(StatesGroup):
    """
    FSM for step-by-step creation of a position (product):
    1) name,
    2) description,
    3) price,
    4) category,
    5) initial stock quantity.
    """
    waiting_item_name = State()
    waiting_item_description = State()
    waiting_item_price = State()
    waiting_category = State()
    waiting_stock_quantity = State()


class UpdateItemFSM(StatesGroup):
    """
    FSM for updating an item:
    1) Manage stock quantity for an existing position.
    2) Full update (name, description, price).
    """
    # Manage stock for an item
    waiting_item_name_for_stock_mgmt = State()
    waiting_stock_action = State()
    waiting_stock_quantity = State()

    # Full update
    waiting_item_name_for_update = State()
    waiting_item_new_name = State()
    waiting_item_description = State()
    waiting_item_price = State()

