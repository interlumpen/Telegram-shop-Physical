from typing import Callable, Iterable, Tuple
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.i18n import localize
from bot.utils import LazyPaginator # noqa: F401


def main_menu(role: int, channel: str | None = None, helper: str | None = None) -> InlineKeyboardMarkup:
    """
    Main menu with shopping cart button.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=localize("btn.shop"), callback_data="shop")
    kb.button(text=localize("btn.cart"), callback_data="view_cart")
    kb.button(text=localize("btn.rules"), callback_data="rules")
    kb.button(text=localize("btn.profile"), callback_data="profile")
    if helper:
        kb.button(text=localize("btn.support"), url=f"tg://user?id={helper}")
    if channel:
        kb.button(text=localize("btn.channel"), url=f"https://t.me/{channel.lstrip('@')}")
    if role > 1:
        kb.button(text=localize("btn.admin_menu"), callback_data="console")
    kb.adjust(2)
    return kb.as_markup()


def profile_keyboard(referral_percent: int, user_items: int = 0) -> InlineKeyboardMarkup:
    """
    Profile keyboard.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=localize("btn.my_orders"), callback_data="my_orders")
    if referral_percent != 0:
        kb.button(text=localize("btn.referral"), callback_data="referral_system")
    if user_items != 0:
        kb.button(text=localize("btn.purchased"), callback_data="bought_items")
    kb.button(text=localize("btn.back"), callback_data="back_to_menu")
    kb.adjust(1)
    return kb.as_markup()


def admin_console_keyboard() -> InlineKeyboardMarkup:
    """
    Admin panel.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=localize("admin.menu.shop"), callback_data="shop_management")
    kb.button(text=localize("admin.menu.goods"), callback_data="goods_management")
    kb.button(text=localize("admin.menu.categories"), callback_data="categories_management")
    kb.button(text=localize("admin.menu.users"), callback_data="user_management")
    kb.button(text=localize("btn.reference_codes"), callback_data="admin_refcode_management")
    kb.button(text=localize("btn.promo_codes"), callback_data="admin_promo_management")
    kb.button(text=localize("btn.settings"), callback_data="settings_management")
    kb.button(text=localize("admin.menu.broadcast"), callback_data="send_message")
    kb.button(text=localize("btn.back"), callback_data="back_to_menu")
    kb.adjust(1)
    return kb.as_markup()


def settings_management_keyboard() -> InlineKeyboardMarkup:
    """
    Settings management keyboard for admin panel.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=localize("btn.referral_bonus_percent"), callback_data="setting_referral_percent")
    kb.button(text=localize("btn.order_timeout"), callback_data="setting_order_timeout")
    kb.button(text=localize("btn.timezone"), callback_data="setting_timezone")
    kb.button(text=localize("btn.back"), callback_data="console")
    kb.adjust(1)
    return kb.as_markup()


def timezone_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Timezone selection keyboard with popular timezones.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 UTC", callback_data="tz_select:UTC")
    kb.button(text="🇷🇺 Moscow (Europe/Moscow)", callback_data="tz_select:Europe/Moscow")
    kb.button(text="🇺🇸 New York (America/New_York)", callback_data="tz_select:America/New_York")
    kb.button(text="🇬🇧 London (Europe/London)", callback_data="tz_select:Europe/London")
    kb.button(text="🇯🇵 Tokyo (Asia/Tokyo)", callback_data="tz_select:Asia/Tokyo")
    kb.button(text="🇩🇪 Berlin (Europe/Berlin)", callback_data="tz_select:Europe/Berlin")
    kb.button(text="✍️ Enter manually", callback_data="tz_manual")
    kb.button(text=localize("btn.back"), callback_data="settings_management")
    kb.adjust(1)
    return kb.as_markup()


def simple_buttons(buttons: Iterable[Tuple[str, str]], per_row: int = 1) -> InlineKeyboardMarkup:
    """
    Universal button assembly from (text, callback_data)
    """
    kb = InlineKeyboardBuilder()
    for text, cb in buttons:
        kb.button(text=text, callback_data=cb)
    kb.adjust(per_row)
    return kb.as_markup()


def back(cb: str = "menu", text: str | None = None) -> InlineKeyboardMarkup:
    """
    One 'Back' button.
    """
    return simple_buttons([(text or localize("btn.back"), cb)])


def close() -> InlineKeyboardMarkup:
    """
    One button 'Close'.
    """
    return simple_buttons([(localize("btn.close"), "close")])


async def lazy_paginated_keyboard(
        paginator: 'LazyPaginator',
        item_text: Callable[[object], str],
        item_callback: Callable[[object], str],
        page: int = 0,
        back_cb: str | None = None,
        nav_cb_prefix: str = "",
        back_text: str | None = None,
) -> InlineKeyboardMarkup:
    """
    Lazy pagination keyboard with data loading on demand
    """
    kb = InlineKeyboardBuilder()

    # Get items for current page
    items = await paginator.get_page(page)

    for item in items:
        kb.button(text=item_text(item), callback_data=item_callback(item))
    kb.adjust(1)

    # Navigation
    total_pages = await paginator.get_total_pages()
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{nav_cb_prefix}{page - 1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{nav_cb_prefix}{page + 1}"))
        kb.row(*nav_buttons)

    if back_cb:
        kb.row(InlineKeyboardButton(text=back_text or localize("btn.back"), callback_data=back_cb))

    return kb.as_markup()


def item_info(item_name: str, back_data: str) -> InlineKeyboardMarkup:
    """
    Product card with Add to Cart button.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=localize("btn.add_to_cart"), callback_data=f"add_to_cart_{item_name}")
    kb.button(text=localize("btn.back"), callback_data=back_data)
    kb.adjust(2)
    return kb.as_markup()


def question_buttons(question: str, back_data: str) -> InlineKeyboardMarkup:
    """
    Universal yes/no + Back.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=localize("btn.yes"), callback_data=f"{question}_yes")
    kb.button(text=localize("btn.no"), callback_data=f"{question}_no")
    kb.button(text=localize("btn.back"), callback_data=back_data)
    kb.adjust(2)
    return kb.as_markup()


def check_sub(channel_username: str) -> InlineKeyboardMarkup:
    """
    checks the channel subscription.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=localize("btn.channel"), url=f"https://t.me/{channel_username}")
    kb.button(text=localize("btn.check_subscription"), callback_data="sub_channel_done")
    kb.adjust(1)
    return kb.as_markup()


def referral_system_keyboard(has_referrals: bool = False, has_earnings: bool = False) -> InlineKeyboardMarkup:
    """
    Referral system keyboard with additional buttons.
    """
    kb = InlineKeyboardBuilder()

    if has_referrals:
        kb.button(text=localize("btn.view_referrals"), callback_data="view_referrals")

    if has_earnings:
        kb.button(text=localize("btn.view_earnings"), callback_data="view_all_earnings")

    # Add reference code management buttons
    kb.button(text=localize("btn.my_reference_codes"), callback_data="my_refcodes")
    kb.button(text=localize("btn.create_reference_code"), callback_data="create_my_refcode")

    kb.button(text=localize("btn.back"), callback_data="profile")
    kb.adjust(1)
    return kb.as_markup()


def reference_code_admin_keyboard():
    """Admin reference code management keyboard"""
    kb = InlineKeyboardBuilder()
    kb.button(text=localize("btn.admin.create_refcode"), callback_data="admin_create_refcode")
    kb.button(text=localize("btn.admin.list_refcodes"), callback_data="admin_list_refcodes")
    kb.button(text=localize("btn.admin.back_to_panel"), callback_data="console")
    kb.adjust(1)
    return kb.as_markup()
