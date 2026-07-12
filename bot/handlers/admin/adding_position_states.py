from urllib.parse import urlparse

from aiogram import Router, F
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound, TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from bot.database.models import Permission
from bot.database.methods import (
    check_category_cached, check_item_cached, create_item
)
from bot.database.methods.inventory import add_inventory
from bot.keyboards.inline import back
from bot.logger_mesh import audit_logger
from bot.filters import HasPermissionFilter
from bot.config import EnvKeys
from bot.i18n import localize
from bot.states import AddItemFSM

router = Router()


@router.callback_query(F.data == 'add_item', HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def add_item_callback_handler(call: CallbackQuery, state):
    """
    Ask administrator for a new position name.
    """
    await call.message.edit_text(localize('admin.goods.add.prompt.name'), reply_markup=back("goods_management"))
    await state.set_state(AddItemFSM.waiting_item_name)


@router.message(AddItemFSM.waiting_item_name, F.text)
async def check_item_name_for_add(message: Message, state):
    """
    If position already exists — inform the user; otherwise save name and ask for description.
    """
    item_name = (message.text or "").strip()
    item = await check_item_cached(item_name)
    if item:
        await message.answer(
            localize('admin.goods.add.name.exists'),
            reply_markup=back('goods_management')
        )
        return

    await state.update_data(item_name=item_name)
    await message.answer(localize('admin.goods.add.prompt.description'), reply_markup=back('goods_management'))
    await state.set_state(AddItemFSM.waiting_item_description)


@router.message(AddItemFSM.waiting_item_description, F.text)
async def add_item_description(message: Message, state):
    """
    Save description and proceed to price input.
    """
    await state.update_data(item_description=(message.text or "").strip())
    await message.answer(localize('admin.goods.add.prompt.price', currency=EnvKeys.PAY_CURRENCY),
                         reply_markup=back('goods_management'))
    await state.set_state(AddItemFSM.waiting_item_price)


@router.message(AddItemFSM.waiting_item_price, F.text)
async def add_item_price(message: Message, state):
    """
    Validate price and ask for category.
    """
    price_text = (message.text or "").strip()
    if not price_text.isdigit():
        await message.answer(localize('admin.goods.add.price.invalid'), reply_markup=back('goods_management'))
        return

    await state.update_data(item_price=int(price_text))
    await message.answer(localize('admin.goods.add.prompt.category'), reply_markup=back('goods_management'))
    await state.set_state(AddItemFSM.waiting_category)


@router.message(AddItemFSM.waiting_category, F.text)
async def check_category_for_add_item(message: Message, state):
    """
    Category must exist; then ask for initial stock quantity.
    """
    category_name = (message.text or "").strip()
    category = await check_category_cached(category_name)
    if not category:
        await message.answer(
            localize('admin.goods.add.category.not_found'),
            reply_markup=back('goods_management')
        )
        return

    await state.update_data(item_category=category_name)
    await message.answer(
        localize('admin.goods.add.stock.prompt'),
        reply_markup=back('goods_management')
    )
    await state.set_state(AddItemFSM.waiting_stock_quantity)


@router.message(AddItemFSM.waiting_stock_quantity, F.text)
async def finish_adding_item(message: Message, state):
    """
    Create position with initial stock quantity and notify group (if configured).
    """
    stock_text = (message.text or "").strip()
    if not stock_text.isdigit():
        await message.answer(
            localize('admin.goods.add.stock.invalid'),
            reply_markup=back('goods_management')
        )
        return

    stock_quantity = int(stock_text)
    if stock_quantity < 0:
        await message.answer(
            localize('admin.goods.add.stock.negative'),
            reply_markup=back('goods_management')
        )
        return

    data = await state.get_data()
    item_name = data.get('item_name')
    item_description = data.get('item_description')
    item_price = data.get('item_price')
    category_name = data.get('item_category')

    # Create position with stock_quantity = 0 initially
    create_item(item_name, item_description, item_price, category_name)

    # Add stock using inventory management system
    if stock_quantity > 0:
        from bot.database import Database
        with Database().session() as session:
            success, msg = add_inventory(
                item_name=item_name,
                quantity=stock_quantity,
                admin_id=message.from_user.id,
                comment="Initial stock added during product creation",
                session=session
            )
            if not success:
                await message.answer(
                    localize('admin.goods.add.stock.error', error=msg),
                    reply_markup=back('goods_management')
                )
                await state.clear()
                return

    await message.answer(
        localize('admin.goods.add.result.created_with_stock',
                 item_name=item_name,
                 stock_quantity=stock_quantity),
        reply_markup=back('goods_management')
    )

    # Optionally notify a channel
    channel_url = EnvKeys.CHANNEL_URL or ""
    parsed = urlparse(channel_url)
    channel_username = (
                           parsed.path.lstrip('/')
                           if parsed.path else channel_url.replace("https://t.me/", "").replace("t.me/", "").lstrip('@')
                       ) or None
    if channel_username:
        try:
            await message.bot.send_message(
                chat_id=f"@{channel_username}",
                text=(
                    f"🎁 {localize('shop.group.new_upload')}\n"
                    f"🏷️ {localize('shop.group.item')}: <b>{item_name}</b>\n"
                    f"📦 {localize('shop.group.stock')}: <b>{stock_quantity}</b>"
                ),
                parse_mode='HTML'
            )
        except TelegramForbiddenError:
            await message.answer(localize("errors.channel.telegram_forbidden_error", channel=channel_username))
        except TelegramNotFound:
            await message.answer(localize("errors.channel.telegram_not_found", channel=channel_username))
        except TelegramBadRequest as e:
            await message.answer(localize("errors.channel.telegram_bad_request", e=e))

    admin_info = await message.bot.get_chat(message.from_user.id)
    audit_logger.info(
        f'Admin {message.from_user.id} ({admin_info.first_name}) created a new item "{item_name}" with stock {stock_quantity}'
    )
    await state.clear()
