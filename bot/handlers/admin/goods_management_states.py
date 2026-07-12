from functools import partial

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from bot.handlers.other import generate_short_hash
from bot.i18n import localize
from bot.database.models import Permission
from bot.database.methods import check_item_cached, delete_item, get_item_info_cached
from bot.database.methods.update import set_item_sale
from bot.database.methods.audit import log_audit
from bot.database.methods.inventory import add_inventory, get_inventory_stats
from bot.keyboards.inline import back, simple_buttons, lazy_paginated_keyboard
from bot.logger_mesh import audit_logger
from bot.filters import HasPermissionFilter
from bot.states import GoodsFSM, UpdateItemFSM
from bot.utils.money import effective_price, format_sale_percent, format_price, as_datetime

router = Router()


@router.callback_query(F.data == 'goods_management', HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def goods_management_callback_handler(call: CallbackQuery, state):
    """
    Opens the positions (goods) management menu.
    """
    actions = [
        (localize("admin.goods.add_position"), "add_item"),
        (localize("admin.goods.manage_stock"), "manage_stock"),
        (localize("admin.goods.update_position"), "update_item"),
        (localize("admin.goods.delete_position"), "delete_item"),
        (localize("admin.goods.view_stock"), "view_stock_status"),
        (localize("admin.goods.manage_discount"), "manage_discount"),
        (localize("btn.back"), "console"),
    ]
    markup = simple_buttons(actions, per_row=1)
    await call.message.edit_text(localize('admin.goods.menu.title'), reply_markup=markup)
    await state.clear()


@router.callback_query(F.data == 'delete_item', HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def delete_item_callback_handler(call: CallbackQuery, state):
    """
    Requests a position name to delete.
    """
    await call.message.edit_text(localize('admin.goods.delete.prompt.name'), reply_markup=back("goods_management"))
    await state.set_state(GoodsFSM.waiting_item_name_delete)


@router.message(GoodsFSM.waiting_item_name_delete, F.text)
async def delete_str_item(message: Message, state):
    """
    Deletes a position by the provided name.
    """
    item_name = message.text
    item = await check_item_cached(item_name)
    if not item:
        await message.answer(
            localize('admin.goods.delete.position.not_found'),
            reply_markup=back('goods_management')
        )
    else:
        delete_item(item_name)
        await message.answer(
            localize('admin.goods.delete.position.success'),
            reply_markup=back('goods_management')
        )
        admin_info = await message.bot.get_chat(message.from_user.id)
        audit_logger.info(
            f'User {message.from_user.id} ({admin_info.first_name}) deleted the position "{item_name}"'
        )
    await state.clear()


@router.callback_query(F.data == 'view_stock_status', HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def view_stock_status_handler(call: CallbackQuery, state):
    """
    Shows inventory status for all products.
    """
    from bot.database import Database
    from bot.database.models.main import Goods

    with Database().session() as session:
        goods = session.query(Goods).all()

        if not goods:
            await call.message.edit_text(
                localize('admin.goods.stock.no_products'),
                reply_markup=back("goods_management")
            )
            return

        text_lines = [localize('admin.goods.stock.status_title'), ""]

        for good in goods:
            available = good.stock_quantity - good.reserved_quantity
            status_emoji = "✅" if available > 0 else "⚠️" if good.stock_quantity > 0 else "❌"
            text_lines.append(
                f"{status_emoji} <b>{good.name}</b>\n"
                f"   📦 Total: {good.stock_quantity} | 🔒 Reserved: {good.reserved_quantity} | "
                f"✨ Available: {available}\n"
            )

        await call.message.edit_text(
            "\n".join(text_lines),
            parse_mode='HTML',
            reply_markup=back("goods_management")
        )
    await state.clear()


@router.callback_query(F.data == 'manage_stock', HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def manage_stock_handler(call: CallbackQuery, state):
    """
    Requests a position name to manage its stock.
    """
    await call.message.edit_text(
        localize('admin.goods.stock.prompt.item_name'),
        reply_markup=back("goods_management")
    )
    await state.set_state(GoodsFSM.waiting_item_name_show)


@router.message(GoodsFSM.waiting_item_name_show, F.text)
async def show_stock_management_options(message: Message, state: FSMContext):
    """
    Shows stock management options for the selected product.
    """
    item_name = message.text.strip()
    item = await check_item_cached(item_name)
    if not item:
        await message.answer(
            localize('admin.goods.position.not_found'),
            reply_markup=back('goods_management')
        )
        await state.clear()
        return

    # Get current stock info
    from bot.database import Database
    from bot.database.models.main import Goods

    with Database().session() as session:
        good = session.query(Goods).filter(Goods.name == item_name).first()
        if not good:
            await message.answer(
                localize('admin.goods.position.not_found'),
                reply_markup=back('goods_management')
            )
            await state.clear()
            return

        available = good.stock_quantity - good.reserved_quantity

        text = (
            f"📦 <b>{localize('admin.goods.stock.management_title', item=item_name)}</b>\n\n"
            f"📊 {localize('admin.goods.stock.current_status')}:\n"
            f"• Total Stock: <b>{good.stock_quantity}</b>\n"
            f"• Reserved: <b>{good.reserved_quantity}</b>\n"
            f"• Available: <b>{available}</b>\n\n"
            f"{localize('admin.goods.stock.select_action')}:"
        )

    await state.update_data(stock_item_name=item_name)

    actions = [
        (localize("admin.goods.stock.set_exact"), f"stock_set_{item_name}"),
        (localize("admin.goods.stock.add_units"), f"stock_add_{item_name}"),
        (localize("admin.goods.stock.remove_units"), f"stock_remove_{item_name}"),
        (localize("btn.back"), "goods_management"),
    ]
    markup = simple_buttons(actions, per_row=1)

    await message.answer(text, parse_mode='HTML', reply_markup=markup)


# Stock management handlers
@router.callback_query(F.data.startswith('stock_set_'), HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def stock_set_handler(call: CallbackQuery, state: FSMContext):
    """
    Prompts admin to set exact stock quantity.
    """
    item_name = call.data.replace('stock_set_', '')
    await state.update_data(stock_item_name=item_name, stock_action='set')
    await call.message.edit_text(
        localize('admin.goods.stock.prompt.set_exact'),
        reply_markup=back("goods_management")
    )
    from bot.states import UpdateItemFSM
    await state.set_state(UpdateItemFSM.waiting_stock_quantity)


@router.callback_query(F.data.startswith('stock_add_'), HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def stock_add_handler(call: CallbackQuery, state: FSMContext):
    """
    Prompts admin to add units to stock.
    """
    item_name = call.data.replace('stock_add_', '')
    await state.update_data(stock_item_name=item_name, stock_action='add')
    await call.message.edit_text(
        localize('admin.goods.stock.prompt.add_units'),
        reply_markup=back("goods_management")
    )
    from bot.states import UpdateItemFSM
    await state.set_state(UpdateItemFSM.waiting_stock_quantity)


@router.callback_query(F.data.startswith('stock_remove_'), HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def stock_remove_handler(call: CallbackQuery, state: FSMContext):
    """
    Prompts admin to remove units from stock.
    """
    item_name = call.data.replace('stock_remove_', '')
    await state.update_data(stock_item_name=item_name, stock_action='remove')
    await call.message.edit_text(
        localize('admin.goods.stock.prompt.remove_units'),
        reply_markup=back("goods_management")
    )
    from bot.states import UpdateItemFSM
    await state.set_state(UpdateItemFSM.waiting_stock_quantity)


# Process stock quantity input
@router.message(UpdateItemFSM.waiting_stock_quantity, F.text)
async def process_stock_quantity(message: Message, state: FSMContext):
    """
    Processes the stock quantity input and applies the action.
    """
    from bot.database import Database
    from bot.database.models.main import Goods

    quantity_text = (message.text or "").strip()
    if not quantity_text.isdigit():
        await message.answer(
            localize('admin.goods.stock.invalid_quantity'),
            reply_markup=back('goods_management')
        )
        return

    quantity = int(quantity_text)
    if quantity < 0:
        await message.answer(
            localize('admin.goods.stock.negative_quantity'),
            reply_markup=back('goods_management')
        )
        return

    data = await state.get_data()
    item_name = data.get('stock_item_name')
    action = data.get('stock_action')

    with Database().session() as session:
        good = session.query(Goods).filter(Goods.name == item_name).first()
        if not good:
            await message.answer(
                localize('admin.goods.position.not_found'),
                reply_markup=back('goods_management')
            )
            await state.clear()
            return

        if action == 'set':
            # Set exact stock quantity
            old_stock = good.stock_quantity
            good.stock_quantity = quantity
            session.commit()

            # Log the change
            from bot.database.methods.inventory import _log_inventory_change
            _log_inventory_change(
                session=session,
                item_name=item_name,
                change_type='manual',
                quantity_change=quantity - old_stock,
                admin_id=message.from_user.id,
                comment=f"Stock set to {quantity} (was {old_stock})"
            )

            await message.answer(
                localize('admin.goods.stock.set_success', item=item_name, quantity=quantity),
                reply_markup=back('goods_management')
            )
            audit_logger.info(
                f'Admin {message.from_user.id} set stock for "{item_name}" to {quantity} (was {old_stock})'
            )

        elif action == 'add':
            # Add units using inventory system
            success, msg = add_inventory(
                item_name=item_name,
                quantity=quantity,
                admin_id=message.from_user.id,
                comment=f"Admin added {quantity} units via stock management",
                session=session
            )
            if success:
                await message.answer(
                    localize('admin.goods.stock.add_success', item=item_name, quantity=quantity),
                    reply_markup=back('goods_management')
                )
                audit_logger.info(
                    f'Admin {message.from_user.id} added {quantity} units to "{item_name}"'
                )
            else:
                await message.answer(
                    localize('admin.goods.stock.error', error=msg),
                    reply_markup=back('goods_management')
                )

        elif action == 'remove':
            # Remove units (manual deduction)
            if quantity > good.stock_quantity:
                await message.answer(
                    localize('admin.goods.stock.insufficient', available=good.stock_quantity),
                    reply_markup=back('goods_management')
                )
                await state.clear()
                return

            old_stock = good.stock_quantity
            good.stock_quantity -= quantity
            session.commit()

            # Log the change
            from bot.database.methods.inventory import _log_inventory_change
            _log_inventory_change(
                session=session,
                item_name=item_name,
                change_type='manual',
                quantity_change=-quantity,
                admin_id=message.from_user.id,
                comment=f"Admin removed {quantity} units via stock management"
            )

            await message.answer(
                localize('admin.goods.stock.remove_success', item=item_name, quantity=quantity),
                reply_markup=back('goods_management')
            )
            audit_logger.info(
                f'Admin {message.from_user.id} removed {quantity} units from "{item_name}"'
            )

    await state.clear()


@router.callback_query(F.data == 'manage_discount', HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def manage_discount_handler(call: CallbackQuery, state: FSMContext):
    """Ask for the product whose discount to manage."""
    await call.message.edit_text(
        localize('admin.goods.sale.prompt.item_name'),
        reply_markup=back("goods_management")
    )
    await state.set_state(GoodsFSM.waiting_sale_item_name)


@router.message(GoodsFSM.waiting_sale_item_name, F.text)
async def sale_show_options(message: Message, state: FSMContext):
    """Show current sale status and offer set/remove actions."""
    item_name = message.text.strip()
    item = await check_item_cached(item_name)
    if not item:
        await message.answer(
            localize('admin.goods.position.not_found'),
            reply_markup=back('goods_management')
        )
        await state.clear()
        return

    final, on_sale, original = effective_price(
        item.get('price'), item.get('sale_percent'), item.get('sale_until')
    )
    if on_sale:
        until_dt = as_datetime(item.get('sale_until'))
        status = localize('admin.goods.sale.current_active',
                          percent=format_sale_percent(item['sale_percent']),
                          price=format_price(final),
                          until=until_dt.strftime('%Y-%m-%d %H:%M') if until_dt else '-')
    else:
        status = localize('admin.goods.sale.current_none')

    await state.update_data(sale_item_name=item_name)
    actions = [
        (localize('admin.goods.sale.set'), f"sale_set_{item_name}"),
        (localize('admin.goods.sale.remove'), f"sale_remove_{item_name}"),
        (localize('btn.back'), 'goods_management'),
    ]
    await message.answer(
        localize('admin.goods.sale.title', item=item_name) + "\n\n" + status,
        parse_mode='HTML',
        reply_markup=simple_buttons(actions, per_row=1)
    )


@router.callback_query(F.data.startswith('sale_set_'), HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def sale_set_start(call: CallbackQuery, state: FSMContext):
    """Prompt for the discount percentage."""
    item_name = call.data.replace('sale_set_', '')
    await state.update_data(sale_item_name=item_name)
    await call.message.edit_text(
        localize('admin.goods.sale.prompt.percent'),
        reply_markup=back('goods_management')
    )
    await state.set_state(GoodsFSM.waiting_sale_percent)


@router.message(GoodsFSM.waiting_sale_percent, F.text)
async def sale_set_percent(message: Message, state: FSMContext):
    """Validate percent, then ask for duration in days."""
    try:
        percent = Decimal((message.text or "").strip().replace(',', '.'))
    except (InvalidOperation, ValueError):
        await message.answer(localize('admin.goods.sale.invalid_percent'))
        return
    if percent <= 0 or percent >= 100:
        await message.answer(localize('admin.goods.sale.invalid_percent'))
        return

    await state.update_data(sale_percent=str(percent))
    await message.answer(
        localize('admin.goods.sale.prompt.days'),
        reply_markup=back('goods_management')
    )
    await state.set_state(GoodsFSM.waiting_sale_days)


@router.message(GoodsFSM.waiting_sale_days, F.text)
async def sale_set_days(message: Message, state: FSMContext):
    """Validate duration, apply the sale."""
    days_text = (message.text or "").strip()
    if not days_text.isdigit() or int(days_text) <= 0:
        await message.answer(localize('admin.goods.sale.invalid_days'))
        return

    days = int(days_text)
    data = await state.get_data()
    item_name = data.get('sale_item_name')
    percent = Decimal(data.get('sale_percent'))
    sale_until = datetime.now(timezone.utc) + timedelta(days=days)

    success, error = set_item_sale(item_name, percent, sale_until)
    if not success:
        await message.answer(
            localize('admin.goods.sale.error', error=error or ''),
            reply_markup=back('goods_management')
        )
        await state.clear()
        return

    log_audit(
        "item_sale_set", user_id=message.from_user.id,
        resource_type="Goods", resource_id=item_name,
        details=f"percent={format_sale_percent(percent)}; until={sale_until.isoformat()}",
    )
    await message.answer(
        localize('admin.goods.sale.set_success',
                 item=item_name, percent=format_sale_percent(percent), days=days),
        reply_markup=back('goods_management')
    )
    await state.clear()


@router.callback_query(F.data.startswith('sale_remove_'), HasPermissionFilter(permission=Permission.SHOP_MANAGE))
async def sale_remove(call: CallbackQuery, state: FSMContext):
    """Remove an active sale from a product."""
    item_name = call.data.replace('sale_remove_', '')
    success, error = set_item_sale(item_name, None, None)
    if success:
        log_audit(
            "item_sale_removed", user_id=call.from_user.id,
            resource_type="Goods", resource_id=item_name,
        )
        await call.message.edit_text(
            localize('admin.goods.sale.remove_success', item=item_name),
            reply_markup=back('goods_management')
        )
    else:
        await call.message.edit_text(
            localize('admin.goods.sale.error', error=error or ''),
            reply_markup=back('goods_management')
        )
    await state.clear()
