from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from bot.database import Database
from bot.database.models.main import CustomerInfo
from bot.database.methods import get_cart_items, calculate_cart_total, add_to_cart, remove_from_cart, clear_cart
from bot.keyboards import back, simple_buttons
from bot.i18n import localize
from bot.config import EnvKeys
from bot.states import CartStates, OrderStates
from bot.handlers.other import is_safe_item_name
from bot.monitoring import get_metrics

router = Router()


@router.callback_query(F.data.startswith('add_to_cart_'))
async def add_to_cart_handler(call: CallbackQuery):
    """
    Handle adding item to cart from item details page
    """
    # Extract item name from callback data: add_to_cart_{item_name}
    item_name = call.data[len('add_to_cart_'):]

    # Validate item name
    if not is_safe_item_name(item_name):
        await call.answer(localize("errors.invalid_item_name"), show_alert=True)
        return

    user_id = call.from_user.id

    # Add to cart
    success, message = await add_to_cart(user_id, item_name, quantity=1)

    if success:
        # Track cart addition
        metrics = get_metrics()
        if metrics:
            metrics.track_event("cart_add", user_id, {
                "item": item_name,
                "quantity": 1
            })
            metrics.track_conversion("customer_journey", "cart_add", user_id)

        await call.answer(localize("cart.add_success", item_name=item_name), show_alert=False)
    else:
        await call.answer(localize("cart.add_error", message=message), show_alert=True)


@router.callback_query(F.data == "view_cart")
async def view_cart_handler(call: CallbackQuery, state: FSMContext):
    """
    Display user's shopping cart
    """
    user_id = call.from_user.id
    cart_items = await get_cart_items(user_id)

    # Track cart view
    if cart_items:
        total = await calculate_cart_total(user_id)
        metrics = get_metrics()
        if metrics:
            metrics.track_event("cart_view", user_id, {
                "items_count": len(cart_items),
                "total": float(total)
            })

    if not cart_items:
        await call.message.edit_text(
            localize("cart.empty"),
            reply_markup=back("back_to_menu")
        )
        return

    # Build cart display
    text = localize("cart.title")

    for item in cart_items:
        text += f"<b>{item['item_name']}</b>\n"
        if item.get('on_sale'):
            text += localize("cart.item.price_format_sale", original=item['original_price'],
                             price=item['price'], currency=EnvKeys.PAY_CURRENCY, quantity=item['quantity']) + "\n"
        else:
            text += localize("cart.item.price_format", price=item['price'],
                             currency=EnvKeys.PAY_CURRENCY, quantity=item['quantity']) + "\n"
        text += localize("cart.item.subtotal_format", subtotal=item['total'], currency=EnvKeys.PAY_CURRENCY) + "\n\n"

    total = await calculate_cart_total(user_id)
    text += localize("cart.total_format", total=total, currency=EnvKeys.PAY_CURRENCY)

    # Build keyboard
    buttons = []
    for item in cart_items:
        buttons.append((localize("btn.remove_item", item_name=item['item_name']), f"remove_cart_{item['cart_id']}"))

    buttons.extend([
        (localize("btn.clear_cart"), "clear_cart"),
        (localize("btn.proceed_checkout"), "checkout_cart"),
        (localize("btn.back"), "back_to_menu")
    ])

    markup = simple_buttons(buttons, per_row=1)

    try:
        await call.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Message content is identical, no need to update
            pass
        else:
            raise
    await state.set_state(CartStates.viewing_cart)


@router.callback_query(F.data.startswith('remove_cart_'))
async def remove_cart_item_handler(call: CallbackQuery, state: FSMContext):
    """
    Remove specific item from cart
    """
    cart_id = int(call.data[len('remove_cart_'):])
    user_id = call.from_user.id

    success, message = await remove_from_cart(cart_id, user_id)

    if success:
        # Track cart item removal
        metrics = get_metrics()
        if metrics:
            metrics.track_event("cart_remove", user_id, {"cart_id": cart_id})

        # Refresh cart view
        await view_cart_handler(call, state)
        await call.answer(localize("cart.removed_success"), show_alert=False)
    else:
        await call.answer(localize("cart.add_error", message=message), show_alert=True)


@router.callback_query(F.data == "clear_cart")
async def clear_cart_handler(call: CallbackQuery):
    """
    Clear all items from cart
    """
    user_id = call.from_user.id

    success, message = await clear_cart(user_id)

    if success:
        # Track cart clearing
        metrics = get_metrics()
        if metrics:
            metrics.track_event("cart_clear", user_id)

        await call.message.edit_text(
            localize("cart.cleared_success"),
            reply_markup=back("back_to_menu")
        )
        await call.answer()
    else:
        await call.answer(localize("cart.add_error", message=message), show_alert=True)


@router.callback_query(F.data == "checkout_cart")
async def checkout_cart_handler(call: CallbackQuery, state: FSMContext):
    """
    Start checkout process - collect delivery information
    """
    user_id = call.from_user.id
    cart_items = await get_cart_items(user_id)

    if not cart_items:
        await call.answer(localize("cart.empty_alert"), show_alert=True)
        return

    # Track checkout start
    metrics = get_metrics()
    if metrics:
        metrics.track_event("checkout_start", user_id)
        metrics.track_conversion("customer_journey", "checkout_start", user_id)

    # Check if user has customer info saved
    from bot.database.models.main import CustomerInfo
    with Database().session() as session:
        customer_info = session.query(CustomerInfo).filter_by(
            telegram_id=user_id
        ).first()

        if customer_info and customer_info.delivery_address and customer_info.phone_number:
            # User has saved info, show summary and ask to confirm or edit
            text = (
                localize("cart.summary_title") +
                localize("cart.saved_delivery_info") +
                localize("cart.delivery_address", address=customer_info.delivery_address) +
                localize("cart.delivery_phone", phone=customer_info.phone_number)
            )
            if customer_info.delivery_note:
                text += localize("cart.delivery_note", note=customer_info.delivery_note)

            text += localize("cart.use_info_question")

            buttons = [
                (localize("btn.use_saved_info"), "confirm_delivery_info"),
                (localize("btn.update_info"), "update_delivery_info"),
                (localize("btn.back_to_cart"), "view_cart")
            ]

            await call.message.edit_text(text, reply_markup=simple_buttons(buttons, per_row=1))
        else:
            # No saved info, start collecting
            await call.message.edit_text(
                localize("order.delivery.address_prompt"),
                reply_markup=back("view_cart")
            )
            await state.set_state(OrderStates.waiting_delivery_address)


@router.callback_query(F.data == "update_delivery_info")
async def update_delivery_info_handler(call: CallbackQuery, state: FSMContext):
    """Start flow to update delivery information"""
    await call.message.edit_text(
        localize("order.delivery.address_prompt"),
        reply_markup=back("view_cart")
    )
    await state.set_state(OrderStates.waiting_delivery_address)


@router.callback_query(F.data == "confirm_delivery_info")
async def confirm_delivery_info_handler(call: CallbackQuery, state: FSMContext):
    """User confirmed using saved delivery info, check for bonuses then proceed to payment"""
    user_id = call.from_user.id

    # Load saved delivery info from CustomerInfo and save to state
    with Database().session() as session:
        customer_info = session.query(CustomerInfo).filter_by(telegram_id=user_id).first()

        if not customer_info or not customer_info.delivery_address or not customer_info.phone_number:
            await call.answer(localize("cart.no_saved_info"), show_alert=True)
            return

        # Save delivery info to state so it can be used when creating the order
        await state.update_data(
            delivery_address=customer_info.delivery_address,
            phone_number=customer_info.phone_number,
            delivery_note=customer_info.delivery_note or ""
        )

    # Import here to avoid circular imports
    from bot.handlers.user.order_handler import check_and_ask_about_bonus
    await call.message.delete()
    await check_and_ask_about_bonus(call.message, state, user_id=user_id, from_callback=True)
