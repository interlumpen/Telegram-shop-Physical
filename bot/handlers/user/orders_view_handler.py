from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.database import Database
from bot.database.models.main import Order, OrderItem
from bot.database.methods import query_user_orders, count_user_orders
from bot.keyboards import back, simple_buttons
from bot.i18n import localize
from bot.config import EnvKeys

router = Router()


@router.callback_query(F.data == "my_orders")
async def my_orders_menu(call: CallbackQuery, state: FSMContext):
    """
    Show orders menu with pending and completed orders counts
    """
    user_id = call.from_user.id

    # Count orders by status
    with Database().session() as session:
        # Count active orders (pending, reserved, confirmed)
        active_count = session.query(Order).filter(
            Order.buyer_id == user_id,
            Order.order_status.in_(['pending', 'reserved', 'confirmed'])
        ).count()

        # Count delivered orders
        delivered_count = session.query(Order).filter(
            Order.buyer_id == user_id,
            Order.order_status == 'delivered'
        ).count()

        total_count = await count_user_orders(user_id)

    text = (
            localize("myorders.title") +
            localize("myorders.total", count=total_count) + "\n" +
            localize("myorders.active", count=active_count) + "\n" +
            localize("myorders.delivered", count=delivered_count) + "\n\n" +
            localize("myorders.select_category")
    )

    buttons = []

    if active_count > 0:
        buttons.append((localize("myorders.active_orders"), "view_orders_active"))

    if delivered_count > 0:
        buttons.append((localize("myorders.delivered_orders"), "view_orders_delivered"))

    if total_count > 0:
        buttons.append((localize("myorders.all_orders"), "view_orders_all"))

    if not buttons:
        text = (
                localize("myorders.title") +
                localize("myorders.no_orders_yet")
        )
        buttons.append((localize("myorders.browse_shop"), "shop"))

    buttons.append((localize("myorders.back"), "profile"))

    markup = simple_buttons(buttons, per_row=1)

    await call.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith('view_orders_'))
async def view_orders_list(call: CallbackQuery, state: FSMContext):
    """
    Show paginated list of orders
    """
    user_id = call.from_user.id

    # Extract status filter from callback data
    status_filter = call.data.replace('view_orders_', '')

    if status_filter == 'all':
        status = None
        title = localize("myorders.all_title")
        # Get all orders
        orders = await query_user_orders(user_id, status=None, limit=10, offset=0)
    elif status_filter == 'active':
        # Active orders: pending, reserved, confirmed
        title = localize("myorders.active_title")
        with Database().session() as session:
            query = session.query(Order).filter(
                Order.buyer_id == user_id,
                Order.order_status.in_(['pending', 'reserved', 'confirmed'])
            ).order_by(Order.created_at.desc())

            active_orders = query.limit(10).offset(0).all()
            orders = []
            for order in active_orders:
                order_items = session.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                items_data = [{
                    'item_name': item.item_name,
                    'price': float(item.price),
                    'quantity': item.quantity
                } for item in order_items]

                orders.append({
                    'id': order.id,
                    'order_code': order.order_code,
                    'total_price': float(order.total_price) if order.total_price else 0,
                    'bonus_applied': float(order.bonus_applied) if order.bonus_applied else 0,
                    'payment_method': order.payment_method,
                    'delivery_address': order.delivery_address,
                    'phone_number': order.phone_number,
                    'delivery_note': order.delivery_note,
                    'bitcoin_address': order.bitcoin_address,
                    'order_status': order.order_status,
                    'created_at': order.created_at,
                    'completed_at': order.completed_at,
                    'delivery_time': order.delivery_time,
                    'items': items_data
                })
    elif status_filter == 'delivered':
        status = 'delivered'
        title = localize("myorders.delivered_title")
        orders = await query_user_orders(user_id, status=status, limit=10, offset=0)
    else:
        await call.answer(localize("myorders.invalid_filter"), show_alert=True)
        return

    if not orders:
        await call.message.edit_text(
            f"{title}\n\n" + localize("myorders.not_found"),
            reply_markup=back("my_orders")
        )
        return

    # Build order list
    text = f"{title}\n\n"

    buttons = []
    for order in orders:
        # Format order summary
        status_emoji = {
            'pending': '⏳',
            'reserved': '🔒',
            'confirmed': '✅',
            'delivered': '📦',
            'cancelled': '❌',
            'canceled': '❌',
            'expired': '⏱️'
        }.get(order['order_status'], '❓')

        date_str = order['created_at'].strftime('%Y-%m-%d %H:%M')

        # Build items summary
        items_count = sum(item['quantity'] for item in order['items'])
        items_names = ', '.join(set(item['item_name'] for item in order['items']))

        order_code_display = order['order_code'] if order.get('order_code') else f"#{order['id']}"
        order_text = localize("myorders.order_summary_format", status_emoji=status_emoji, code=order_code_display,
                              items_count=items_count, total=order['total_price'], currency=EnvKeys.PAY_CURRENCY)
        buttons.append((order_text, f"view_order_{order['id']}"))

    buttons.append((localize("myorders.back_to_menu"), "my_orders"))

    markup = simple_buttons(buttons, per_row=1)

    await call.message.edit_text(text + localize("myorders.select_details"), reply_markup=markup)


@router.callback_query(F.data.startswith('view_order_'))
async def view_order_details(call: CallbackQuery, state: FSMContext):
    """
    Show detailed information about a specific order
    """
    user_id = call.from_user.id
    order_id = int(call.data.replace('view_order_', ''))

    # Get order details
    with Database().session() as session:
        order = session.query(Order).filter(
            Order.id == order_id,
            Order.buyer_id == user_id
        ).first()

        if not order:
            await call.answer(localize("myorders.order_not_found"), show_alert=True)
            return

        # Get order items
        order_items = session.query(OrderItem).filter(OrderItem.order_id == order.id).all()

        # Build order details text
        status_display = {
            'pending': '⏳ Pending',
            'reserved': '🔒 Reserved',
            'confirmed': '✅ Confirmed',
            'delivered': '📦 Delivered',
            'cancelled': '❌ Cancelled',
            'canceled': '❌ Canceled',
            'expired': '⏱️ Expired'
        }.get(order.order_status, '❓ Unknown')

        order_code_display = order.order_code if order.order_code else f"#{order.id}"
        text = (
                localize("myorders.detail.title", order_code=order_code_display) +
                localize("myorders.detail.status", status=status_display)
        )

        # Show bonus if applied
        if order.bonus_applied and order.bonus_applied > 0:
            text += localize("myorders.detail.subtotal", subtotal=order.total_price)
            text += localize("myorders.detail.bonus_applied", bonus=order.bonus_applied)
            final_price = order.total_price - order.bonus_applied
            text += localize("myorders.detail.final_price", total=final_price)
        else:
            text += localize("myorders.detail.total_price", total=order.total_price)

        text += localize("myorders.detail.payment_method", method=order.payment_method.upper())
        text += localize("myorders.detail.ordered", date=order.created_at.strftime('%Y-%m-%d %H:%M'))

        # Show delivery time if set
        if order.delivery_time:
            text += localize("myorders.detail.delivery_time", time=order.delivery_time.strftime('%Y-%m-%d %H:%M'))

        if order.completed_at:
            text += localize("myorders.detail.completed", date=order.completed_at.strftime('%Y-%m-%d %H:%M'))

        # Show items
        items_text = ""
        for item in order_items:
            items_text += f"• {item.item_name} x{item.quantity} - {item.price * item.quantity} {EnvKeys.PAY_CURRENCY}\n"

        text += localize("myorders.detail.items", items=items_text)

        text += localize(
            "myorders.detail.delivery_info",
            address=localize("cart.delivery_address", address=order.delivery_address).rstrip("\n"),
            phone=localize("cart.delivery_phone", phone=order.phone_number).rstrip("\n"),
            note=localize("cart.delivery_note", note=order.delivery_note).rstrip("\n") if order.delivery_note else "",
        )

        # Show payment info based on payment method and status
        if order.order_status in ('reserved', 'pending'):
            if order.payment_method == 'bitcoin' and order.bitcoin_address:
                # Bitcoin payment instructions
                final_price = order.total_price - (order.bonus_applied if order.bonus_applied else 0)
                text += (
                        "\n" + localize("myorders.detail.payment_info_title") + "\n" +
                        localize("myorders.detail.bitcoin_address_label") + ":\n"
                                                                            f"<code>{order.bitcoin_address}</code>\n\n" +
                        localize("myorders.detail.bitcoin_send_instruction", amount=final_price,
                                 currency=EnvKeys.PAY_CURRENCY) + "\n" +
                        localize("myorders.detail.bitcoin_admin_confirm")
                )
            elif order.payment_method == 'cash':
                # Cash on delivery instructions
                text += (
                        "\n" + localize("myorders.detail.cash_title") + "\n" +
                        localize("myorders.detail.cash_awaiting_confirm") + "\n" +
                        localize("myorders.detail.cash_will_notify") + "\n" +
                        localize("myorders.detail.cash_payment_courier")
                )

        # Show confirmation status
        if order.order_status == 'confirmed':
            text += "\n" + localize("myorders.detail.confirmed_title") + "\n"
            if order.delivery_time:
                text += localize("myorders.detail.scheduled_delivery_label",
                                 time=order.delivery_time.strftime('%Y-%m-%d %H:%M')) + "\n"
            text += localize("myorders.detail.preparing_message") + "\n"

        # Show delivery confirmation
        if order.order_status == 'delivered':
            text += "\n" + localize("myorders.detail.delivered_title") + "\n"
            text += localize("myorders.detail.delivered_thanks_message") + "\n"

        # Map order status to view filter
        if order.order_status in ('reserved', 'pending', 'confirmed'):
            view_filter = 'active'
        elif order.order_status == 'delivered':
            view_filter = 'delivered'
        else:
            # For expired, canceled, cancelled, etc. - go to all orders
            view_filter = 'all'

        buttons = [
            (localize("btn.back_to_orders"), f"view_orders_{view_filter}")
        ]

        # Add help button for pending orders
        if order.order_status in ('reserved', 'pending') and order.payment_method == 'bitcoin':
            buttons.insert(0, (localize("btn.need_help"), "help_pending_order"))

        markup = simple_buttons(buttons, per_row=1)

        await call.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data == "help_pending_order")
async def help_pending_order(call: CallbackQuery):
    """
    Show help message for pending orders
    """
    text = (
            localize("help.pending_order.title") + "\n\n" +
            localize("help.pending_order.status") + "\n\n" +
            localize("help.pending_order.what_to_do_title") + "\n" +
            localize("help.pending_order.step1") + "\n" +
            localize("help.pending_order.step2") + "\n" +
            localize("help.pending_order.step3") + "\n" +
            localize("help.pending_order.step4") + "\n\n" +
            localize("help.pending_order.issues_title") + "\n" +
            localize("help.pending_order.contact_support")
    )

    await call.message.edit_text(
        text,
        reply_markup=back("my_orders")
    )
