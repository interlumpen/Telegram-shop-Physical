from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
import html
from decimal import Decimal

from bot.database import Database
from bot.database.models.main import Order, OrderItem, CustomerInfo, ShoppingCart
from bot.database.methods import reserve_inventory, get_cart_items, calculate_cart_total, \
    validate_promo_code, record_promo_usage
from bot.keyboards import back, simple_buttons
from bot.i18n import localize
from bot.config import EnvKeys
from bot.states import OrderStates
from bot.logger_mesh import logger
from bot.payments.bitcoin import get_available_bitcoin_address, mark_bitcoin_address_used
from bot.export import log_order_creation, sync_customer_to_csv
from bot.utils import generate_unique_order_code, get_telegram_username
from bot.utils.money import format_price
from bot.monitoring import get_metrics

router = Router()


@router.message(OrderStates.waiting_delivery_address)
async def process_delivery_address(message: Message, state: FSMContext):
    """
    Collect delivery address from user
    """
    delivery_address = message.text.strip()

    if len(delivery_address) < 5:
        await message.answer(
            localize("order.delivery.address_invalid"),
            reply_markup=back("view_cart")
        )
        return

    # Save to state
    await state.update_data(delivery_address=delivery_address)

    # Ask for phone number
    await message.answer(
        localize("order.delivery.phone_prompt"),
        reply_markup=back("view_cart")
    )
    await state.set_state(OrderStates.waiting_phone_number)


@router.message(OrderStates.waiting_phone_number)
async def process_phone_number(message: Message, state: FSMContext):
    """
    Collect phone number from user
    """
    phone_number = message.text.strip()

    if len(phone_number) < 8:
        await message.answer(
            localize("order.delivery.phone_invalid"),
            reply_markup=back("view_cart")
        )
        return

    # Save to state
    await state.update_data(phone_number=phone_number)

    # Ask for delivery note (optional)
    await message.answer(
        localize("order.delivery.note_prompt"),
        reply_markup=simple_buttons([(localize("btn.skip"), "skip_delivery_note"), (localize("btn.back"), "view_cart")],
                                    per_row=2)
    )
    await state.set_state(OrderStates.waiting_delivery_note)


@router.message(OrderStates.waiting_delivery_note)
async def process_delivery_note(message: Message, state: FSMContext):
    """
    Collect delivery note from user
    """
    delivery_note = message.text.strip()

    # Save to state
    await state.update_data(delivery_note=delivery_note)

    # Offer an optional promo code before the bonus step
    await ask_promo_code(message, state, user_id=message.from_user.id)


@router.callback_query(F.data == "skip_delivery_note", OrderStates.waiting_delivery_note)
async def skip_delivery_note_handler(call: CallbackQuery, state: FSMContext):
    """
    User skipped delivery note
    """
    await state.update_data(delivery_note="")

    # Offer an optional promo code before the bonus step
    await call.message.delete()
    await ask_promo_code(call.message, state, user_id=call.from_user.id)


async def ask_promo_code(message: Message, state: FSMContext, user_id: int = None):
    """Prompt the user to enter an optional promo code (or skip)."""
    await message.answer(
        localize("order.promo.prompt"),
        reply_markup=simple_buttons([
            (localize("btn.promo.skip"), "skip_promo"),
            (localize("btn.back"), "view_cart"),
        ], per_row=1)
    )
    await state.set_state(OrderStates.waiting_promo_code)


@router.message(OrderStates.waiting_promo_code, F.text)
async def process_promo_code(message: Message, state: FSMContext):
    """Validate an entered promo code against the current cart."""
    from bot.database.methods import validate_promo_code
    user_id = message.from_user.id
    code = message.text.strip().upper()

    cart_items = await get_cart_items(user_id)
    if not cart_items:
        await message.answer(localize("cart.empty_alert"), reply_markup=back("shop"))
        await state.clear()
        return

    valid, error_key, discount, _promo = validate_promo_code(code, user_id, cart_items)
    if not valid:
        await message.answer(
            localize(error_key),
            reply_markup=simple_buttons([
                (localize("btn.promo.skip"), "skip_promo"),
                (localize("btn.back"), "view_cart"),
            ], per_row=1)
        )
        return

    await state.update_data(promo_code=code, promo_discount=str(discount))
    await message.answer(localize("order.promo.applied", code=code, amount=format_price(discount)))
    await check_and_ask_about_bonus(message, state, user_id=user_id)


@router.callback_query(F.data == "skip_promo", OrderStates.waiting_promo_code)
async def skip_promo_handler(call: CallbackQuery, state: FSMContext):
    """User skipped the promo code step."""
    await state.update_data(promo_code=None, promo_discount="0")
    await call.message.delete()
    await check_and_ask_about_bonus(call.message, state, user_id=call.from_user.id, from_callback=True)


async def check_and_ask_about_bonus(message: Message, state: FSMContext, user_id: int = None,
                                    from_callback: bool = False):
    """
    Check if user has referral bonus and ask if they want to apply it to the order
    """
    if user_id is None:
        user_id = message.from_user.id

    # Get user's bonus balance from CustomerInfo
    with Database().session() as session:
        customer_info = session.query(CustomerInfo).filter_by(telegram_id=user_id).first()

        if customer_info and customer_info.bonus_balance and customer_info.bonus_balance > 0:
            bonus_balance = customer_info.bonus_balance

            # Calculate cart total to show in message
            total_amount = await calculate_cart_total(user_id)

            # Save bonus_balance in state for later use
            await state.update_data(available_bonus=float(bonus_balance))

            text = (
                    localize("order.bonus.available", bonus_balance=bonus_balance) +
                    localize("order.bonus.order_total_label", amount=total_amount,
                             currency=EnvKeys.PAY_CURRENCY) + "\n\n" +
                    localize("order.bonus.apply_question") + f"\n" +
                    localize("order.bonus.choose_amount_hint", max_amount=min(bonus_balance, total_amount))
            )

            await message.answer(
                text,
                reply_markup=simple_buttons([
                    (localize("btn.apply_bonus_yes"), "apply_bonus_yes"),
                    (localize("btn.apply_bonus_no"), "apply_bonus_no")
                ], per_row=2)
            )
            return

    # No bonus or zero bonus - proceed to payment
    await state.update_data(bonus_applied=0)
    await finalize_order_and_payment(message, state, user_id=user_id, from_callback=from_callback)


@router.callback_query(F.data == "apply_bonus_yes")
async def apply_bonus_yes_handler(call: CallbackQuery, state: FSMContext):
    """
    User wants to apply bonus - ask for amount
    """
    data = await state.get_data()
    available_bonus = Decimal(str(data.get('available_bonus', 0)))

    total_amount = await calculate_cart_total(call.from_user.id)
    max_applicable = min(available_bonus, Decimal(str(total_amount)))

    await call.message.edit_text(
        localize("order.bonus.enter_amount_title") + "\n\n" +
        localize("order.bonus.available_label", amount=available_bonus) + "\n" +
        localize("order.bonus.order_total_label", amount=total_amount, currency=EnvKeys.PAY_CURRENCY) + "\n" +
        localize("order.bonus.max_applicable_label", amount=max_applicable) + "\n\n" +
        localize("order.bonus.enter_amount", max_applicable=max_applicable),
        reply_markup=simple_buttons([
            (localize("btn.use_all_bonus", amount=max_applicable), f"use_all_bonus_{max_applicable}"),
            (localize("btn.cancel"), "apply_bonus_no")
        ], per_row=2)
    )
    await state.set_state(OrderStates.waiting_bonus_amount)


@router.callback_query(F.data.startswith("use_all_bonus_"))
async def use_all_bonus_handler(call: CallbackQuery, state: FSMContext):
    """
    User wants to use all available bonus
    """
    # Extract amount from callback data
    amount_str = call.data.replace("use_all_bonus_", "")
    bonus_amount = Decimal(amount_str)

    await state.update_data(bonus_applied=float(bonus_amount))
    await call.message.delete()
    await finalize_order_and_payment(call.message, state, user_id=call.from_user.id, from_callback=True)


@router.message(OrderStates.waiting_bonus_amount)
async def process_bonus_amount(message: Message, state: FSMContext):
    """
    Process the bonus amount entered by user
    """
    try:
        bonus_amount = Decimal(message.text.strip())

        if bonus_amount <= 0:
            await message.answer(localize("order.bonus.amount_positive_error"))
            return

        data = await state.get_data()
        available_bonus = Decimal(str(data.get('available_bonus', 0)))
        total_amount = await calculate_cart_total(message.from_user.id)
        max_applicable = min(available_bonus, Decimal(str(total_amount)))

        if bonus_amount > max_applicable:
            await message.answer(
                localize("order.bonus.amount_too_high", max_applicable=max_applicable)
            )
            return

        # Valid amount - save and proceed
        await state.update_data(bonus_applied=float(bonus_amount))
        await finalize_order_and_payment(message, state, user_id=message.from_user.id)

    except (ValueError, TypeError):
        await message.answer(localize("order.bonus.invalid_amount"))


@router.callback_query(F.data == "apply_bonus_no")
async def apply_bonus_no_handler(call: CallbackQuery, state: FSMContext):
    """
    User doesn't want to apply bonus
    """
    await state.update_data(bonus_applied=0)
    await call.message.delete()
    await finalize_order_and_payment(call.message, state, user_id=call.from_user.id, from_callback=True)


async def show_payment_method_selection(message: Message, state: FSMContext, user_id: int = None):
    """
    Show payment method selection (Bitcoin or Cash)
    """
    if user_id is None:
        user_id = message.from_user.id

    # Get cart total
    cart_total = await calculate_cart_total(user_id)
    data = await state.get_data()
    bonus_applied = Decimal(str(data.get('bonus_applied', 0)))
    promo_code = data.get('promo_code')
    promo_discount = Decimal(str(data.get('promo_discount', 0) or 0))
    final_amount = max(Decimal('0'), cart_total - bonus_applied - promo_discount)

    # Get localized strings
    text = localize("order.payment_method.choose")

    summary_text = (
            localize("order.summary.title") +
            localize("order.summary.cart_total", cart_total=cart_total) + "\n"
    )

    if promo_discount > 0:
        summary_text += localize("order.summary.promo_applied", code=promo_code,
                                 promo_discount=promo_discount) + "\n"
    if bonus_applied > 0:
        summary_text += localize("order.summary.bonus_applied", bonus_applied=bonus_applied) + "\n"

    if promo_discount > 0 or bonus_applied > 0:
        summary_text += f"<b>" + localize("order.summary.final_amount", final_amount=final_amount) + "</b>\n\n"
    else:
        summary_text += localize("order.summary.total_label", amount=final_amount,
                                 currency=EnvKeys.PAY_CURRENCY) + "\n\n"

    summary_text += text

    # Payment method buttons
    bitcoin_text = localize("order.payment_method.bitcoin")
    cash_text = localize("order.payment_method.cash")

    await message.answer(
        summary_text,
        reply_markup=simple_buttons([
            (bitcoin_text, "payment_method_bitcoin"),
            (cash_text, "payment_method_cash")
        ], per_row=2)
    )

    await state.set_state(OrderStates.waiting_payment_method)


@router.callback_query(F.data == "payment_method_bitcoin", OrderStates.waiting_payment_method)
async def payment_method_bitcoin_handler(call: CallbackQuery, state: FSMContext):
    """
    User selected Bitcoin payment
    """
    await call.answer()
    await state.update_data(payment_method='bitcoin')

    # Track payment method selection
    metrics = get_metrics()
    if metrics:
        metrics.track_event("payment_bitcoin_initiated", call.from_user.id)
        metrics.track_conversion("customer_journey", "payment_initiated", call.from_user.id)

    # Proceed to Bitcoin payment
    await process_bitcoin_payment_new_message(call.message, state, user_id=call.from_user.id)


@router.callback_query(F.data == "payment_method_cash", OrderStates.waiting_payment_method)
async def payment_method_cash_handler(call: CallbackQuery, state: FSMContext):
    """
    User selected Cash payment
    """
    await call.answer()
    await state.update_data(payment_method='cash')

    # Track payment method selection
    metrics = get_metrics()
    if metrics:
        metrics.track_event("payment_cash_initiated", call.from_user.id)
        metrics.track_conversion("customer_journey", "payment_initiated", call.from_user.id)

    # Proceed to Cash payment
    await process_cash_payment_new_message(call.message, state, user_id=call.from_user.id)


async def finalize_order_and_payment(message: Message, state: FSMContext, user_id: int = None,
                                     from_callback: bool = False):
    """
    Save customer info and proceed to payment method selection
    """
    if user_id is None:
        user_id = message.from_user.id

    # Get real username from Telegram API
    username = await get_telegram_username(user_id, message.bot)

    # Get data from state
    data = await state.get_data()
    delivery_address = data.get('delivery_address')
    phone_number = data.get('phone_number')
    delivery_note = data.get('delivery_note', '')

    # Save/update customer info
    try:
        with Database().session() as session:
            customer_info = session.query(CustomerInfo).filter_by(
                telegram_id=user_id
            ).first()

            if customer_info:
                # Log changes
                from bot.export.custom_logging import log_customer_info_change

                if customer_info.delivery_address != delivery_address:
                    log_customer_info_change(
                        user_id, username, "ADDRESS",
                        customer_info.delivery_address, delivery_address
                    )
                    customer_info.delivery_address = delivery_address

                if customer_info.phone_number != phone_number:
                    log_customer_info_change(
                        user_id, username, "PHONE",
                        customer_info.phone_number, phone_number
                    )
                    customer_info.phone_number = phone_number

                if customer_info.delivery_note != delivery_note:
                    log_customer_info_change(
                        user_id, username, "DELIVERY_NOTE",
                        customer_info.delivery_note, delivery_note
                    )
                    customer_info.delivery_note = delivery_note

            else:
                # Create new customer info (username stored in users table, not here)
                customer_info = CustomerInfo(
                    telegram_id=user_id,
                    phone_number=phone_number,
                    delivery_address=delivery_address,
                    delivery_note=delivery_note
                )
                session.add(customer_info)

            session.commit()

    except Exception as e:
        logger.error(f"Error saving customer info: {e}")
        await message.answer(
            localize("order.delivery.info_save_error"),
            reply_markup=back("view_cart")
        )
        return

    # Show payment method selection
    await show_payment_method_selection(message, state, user_id=user_id)


async def process_bitcoin_payment_new_message(message: Message, state: FSMContext, user_id: int = None):
    """
    Process Bitcoin payment by sending a new message
    """
    if user_id is None:
        user_id = message.from_user.id

    # Get real username from Telegram API
    username = await get_telegram_username(user_id, message.bot)

    # Get cart items
    cart_items = await get_cart_items(user_id)

    if not cart_items:
        await message.answer(localize("cart.empty_alert"), reply_markup=back("shop"))
        return

    # Calculate total
    total_amount = await calculate_cart_total(user_id)

    # Get bonus_applied from state
    data = await state.get_data()
    bonus_applied = Decimal(str(data.get('bonus_applied', 0)))

    # Re-validate any promo code against the current cart (authoritative discount)
    promo_code = data.get('promo_code')
    promo_discount = Decimal('0')
    if promo_code:
        p_valid, _p_err, p_disc, _p = validate_promo_code(promo_code, user_id, cart_items)
        promo_discount = p_disc if p_valid else Decimal('0')
        if not p_valid:
            promo_code = None

    # Calculate final amount after bonus and promo
    final_amount = max(Decimal('0'), total_amount - bonus_applied - promo_discount)

    # Get customer info
    with Database().session() as session:
        customer_info = session.query(CustomerInfo).filter_by(
            telegram_id=user_id
        ).first()

        if not customer_info:
            await message.answer(
                localize("order.payment.customer_not_found"),
                reply_markup=back("view_cart")
            )
            return

        # Atomically pick and lock an unused Bitcoin address within this
        # transaction (FOR UPDATE SKIP LOCKED), so two concurrent checkouts can
        # never be assigned the same address.
        btc_address = get_available_bitcoin_address(session=session)
        if not btc_address:
            await message.answer(
                localize("order.payment.system_unavailable"),
                reply_markup=back("back_to_menu")
            )
            return

        # Deduct bonus from customer's bonus_balance if applied
        if bonus_applied > 0:
            if customer_info.bonus_balance < bonus_applied:
                await message.answer(
                    localize("order.bonus.insufficient"),
                    reply_markup=back("view_cart")
                )
                return
            customer_info.bonus_balance -= bonus_applied

        # Create one order for entire cart
        try:
            items_summary = []

            # Create the main order
            order = Order(
                buyer_id=user_id,
                total_price=Decimal(str(total_amount)),
                bonus_applied=bonus_applied,
                promo_code=promo_code,
                promo_discount=promo_discount,
                payment_method="bitcoin",
                delivery_address=customer_info.delivery_address,
                phone_number=customer_info.phone_number,
                delivery_note=customer_info.delivery_note or "",
                bitcoin_address=btc_address,
                order_status="pending"
            )
            session.add(order)
            session.flush()  # Get the order ID

            # Generate unique order code
            order.order_code = generate_unique_order_code(session)

            # Record promo usage inside this transaction (once per user enforced by
            # the unique constraint; current_uses bumped under a row lock).
            if promo_code and promo_discount > 0:
                record_promo_usage(promo_code, user_id, order.id, promo_discount, session)

            # Process each cart item and create OrderItems
            items_to_reserve = []
            for cart_item in cart_items:
                item_name = cart_item['item_name']
                quantity = cart_item['quantity']
                price = cart_item['price']

                # Create OrderItem (without item_values - physical goods)
                order_item = OrderItem(
                    order_id=order.id,
                    item_name=item_name,
                    price=Decimal(str(price)),
                    quantity=quantity
                )
                session.add(order_item)

                items_summary.append(f"{item_name} x{quantity} = {cart_item['total']} {EnvKeys.PAY_CURRENCY}")

                # Prepare for inventory reservation
                items_to_reserve.append({
                    'item_name': item_name,
                    'quantity': quantity
                })

            # Reserve inventory for this order (extended timeout for bitcoin - 7 days)
            success, reserve_message = reserve_inventory(order.id, items_to_reserve, payment_method='bitcoin',
                                                         session=session)
            if not success:
                session.rollback()
                await message.answer(
                    localize("order.inventory.unable_to_reserve", unavailable_items=reserve_message),
                    reply_markup=back("view_cart")
                )
                return

            # Mark Bitcoin address as used with this order
            mark_bitcoin_address_used(btc_address, user_id, username, order.id, session=session,
                                      order_code=order.order_code)

            # Log order creation
            log_order_creation(
                order_id=order.id,
                buyer_id=user_id,
                buyer_username=username,
                items_summary="\n".join(items_summary),
                total_price=float(total_amount),
                payment_method="bitcoin",
                delivery_address=customer_info.delivery_address,
                phone_number=customer_info.phone_number,
                bitcoin_address=btc_address,
                order_code=order.order_code
            )

            # Clear cart
            session.query(ShoppingCart).filter_by(user_id=user_id).delete()

            session.commit()

            # Track order creation metrics
            metrics = get_metrics()
            if metrics:
                metrics.track_event("order_created", user_id, {
                    "order_code": order.order_code,
                    "payment_method": "bitcoin",
                    "total": float(total_amount),
                    "bonus_applied": float(bonus_applied)
                })
                # Track inventory reservation
                for item in items_to_reserve:
                    metrics.track_event("inventory_reserved", user_id, {
                        "item": item['item_name'],
                        "quantity": item['quantity'],
                        "order_code": order.order_code
                    })
                # Track bonus usage if applied
                if bonus_applied > 0:
                    metrics.track_event("payment_bonus_applied", user_id, {
                        "bonus_amount": float(bonus_applied),
                        "order_code": order.order_code
                    })

            # Send payment instructions to user
            payment_text = (
                    localize("order.payment.bitcoin.title") + "\n\n" +
                    localize("order.payment.bitcoin.order_code", code=order.order_code) + "\n" +
                    localize("order.payment.subtotal_label", amount=total_amount, currency=EnvKeys.PAY_CURRENCY) + "\n"
            )

            if promo_discount > 0:
                payment_text += localize("order.payment.promo_applied_label", code=promo_code,
                                         amount=promo_discount, currency=EnvKeys.PAY_CURRENCY) + "\n"
            if bonus_applied > 0:
                payment_text += localize("order.payment.bonus_applied_label", amount=bonus_applied,
                                         currency=EnvKeys.PAY_CURRENCY) + "\n"
            if promo_discount > 0 or bonus_applied > 0:
                payment_text += localize("order.payment.final_amount_label", amount=final_amount,
                                         currency=EnvKeys.PAY_CURRENCY) + "\n\n"
            else:
                payment_text += localize("order.payment.total_amount_label", amount=total_amount,
                                         currency=EnvKeys.PAY_CURRENCY) + "\n\n"

            payment_text += (
                    localize("order.payment.bitcoin.items_title") + "\n"
                                                                    f"{chr(10).join(items_summary)}\n\n" +
                    localize("order.payment.bitcoin.delivery_title") + "\n" +
                    localize("cart.delivery_address", address=customer_info.delivery_address) +
                    localize("cart.delivery_phone", phone=customer_info.phone_number)
            )

            if customer_info.delivery_note:
                payment_text += localize("cart.delivery_note", note=customer_info.delivery_note)

            payment_text += (
                    "\n" + localize("order.payment.bitcoin.address_title") + "\n"
                                                                             f"<code>{btc_address}</code>\n\n" +
                    localize("order.payment.bitcoin.important_title") + "\n" +
                    localize("order.payment.bitcoin.send_exact") + "\n" +
                    localize("order.payment.bitcoin.one_time_address") + "\n" +
                    localize("order.payment.bitcoin.admin_confirm") + "\n\n" +
                    localize("order.payment.bitcoin.need_help")
            )

            await message.answer(
                payment_text,
                reply_markup=back("back_to_menu")
            )

            # Notify admin
            await notify_admin_new_order(
                message.bot, order.order_code, user_id, username,
                "\n".join(items_summary), total_amount, btc_address,
                customer_info.delivery_address, customer_info.phone_number,
                customer_info.delivery_note or "", bonus_applied, final_amount
            )

            # Sync customer CSV
            sync_customer_to_csv(user_id, username)

            await state.clear()

        except Exception as e:
            session.rollback()
            logger.error(f"Error creating orders: {e}")
            await message.answer(
                localize("order.payment.error_general"),
                reply_markup=back("view_cart")
            )
            return


async def process_cash_payment_new_message(message: Message, state: FSMContext, user_id: int = None):
    """
    Process Cash on Delivery payment by sending a new message
    """
    if user_id is None:
        user_id = message.from_user.id

    # Get real username from Telegram API
    username = await get_telegram_username(user_id, message.bot)

    # Get cart items
    cart_items = await get_cart_items(user_id)

    if not cart_items:
        await message.answer(localize("cart.empty_alert"), reply_markup=back("shop"))
        return

    # Calculate total
    total_amount = await calculate_cart_total(user_id)

    # Get bonus_applied from state
    data = await state.get_data()
    bonus_applied = Decimal(str(data.get('bonus_applied', 0)))

    # Re-validate any promo code against the current cart (authoritative discount)
    promo_code = data.get('promo_code')
    promo_discount = Decimal('0')
    if promo_code:
        p_valid, _p_err, p_disc, _p = validate_promo_code(promo_code, user_id, cart_items)
        promo_discount = p_disc if p_valid else Decimal('0')
        if not p_valid:
            promo_code = None

    # Calculate final amount after bonus and promo
    final_amount = max(Decimal('0'), total_amount - bonus_applied - promo_discount)

    # Get customer info
    with Database().session() as session:
        customer_info = session.query(CustomerInfo).filter_by(
            telegram_id=user_id
        ).first()

        if not customer_info:
            await message.answer(
                localize("order.payment.customer_not_found"),
                reply_markup=back("view_cart")
            )
            return

        # Deduct bonus from customer's bonus_balance if applied
        if bonus_applied > 0:
            if customer_info.bonus_balance < bonus_applied:
                await message.answer(
                    localize("order.bonus.insufficient"),
                    reply_markup=back("view_cart")
                )
                return
            customer_info.bonus_balance -= bonus_applied

        # Create one order for entire cart
        try:
            items_summary = []

            # Create the main order (cash payment - no Bitcoin address)
            order = Order(
                buyer_id=user_id,
                total_price=Decimal(str(total_amount)),
                bonus_applied=bonus_applied,
                promo_code=promo_code,
                promo_discount=promo_discount,
                payment_method="cash",
                delivery_address=customer_info.delivery_address,
                phone_number=customer_info.phone_number,
                delivery_note=customer_info.delivery_note or "",
                bitcoin_address=None,  # No Bitcoin address for cash
                order_status="pending"
            )
            session.add(order)
            session.flush()  # Get the order ID

            # Generate unique order code
            order.order_code = generate_unique_order_code(session)

            # Record promo usage inside this transaction.
            if promo_code and promo_discount > 0:
                record_promo_usage(promo_code, user_id, order.id, promo_discount, session)

            # Process each cart item and create OrderItems
            items_to_reserve = []
            for cart_item in cart_items:
                item_name = cart_item['item_name']
                quantity = cart_item['quantity']
                price = cart_item['price']

                # Create OrderItem (without item_values - physical goods)
                order_item = OrderItem(
                    order_id=order.id,
                    item_name=item_name,
                    price=Decimal(str(price)),
                    quantity=quantity
                )
                session.add(order_item)

                items_summary.append(f"{item_name} x{quantity} = {cart_item['total']} {EnvKeys.PAY_CURRENCY}")

                # Prepare for inventory reservation
                items_to_reserve.append({
                    'item_name': item_name,
                    'quantity': quantity
                })

            # Reserve inventory for this order (configurable timeout for cash - default 24 hours)
            success, reserve_message = reserve_inventory(order.id, items_to_reserve, payment_method='cash',
                                                         session=session)
            if not success:
                session.rollback()
                await message.answer(
                    localize("order.inventory.unable_to_reserve", unavailable_items=reserve_message),
                    reply_markup=back("view_cart")
                )
                return

            # Log order creation
            log_order_creation(
                order_id=order.id,
                buyer_id=user_id,
                buyer_username=username,
                items_summary="\n".join(items_summary),
                total_price=float(total_amount),
                payment_method="cash",
                delivery_address=customer_info.delivery_address,
                phone_number=customer_info.phone_number,
                bitcoin_address=None,
                order_code=order.order_code
            )

            # Clear cart
            session.query(ShoppingCart).filter_by(user_id=user_id).delete()

            session.commit()

            # Track order creation metrics
            metrics = get_metrics()
            if metrics:
                metrics.track_event("order_created", user_id, {
                    "order_code": order.order_code,
                    "payment_method": "cash",
                    "total": float(total_amount),
                    "bonus_applied": float(bonus_applied)
                })
                # Track inventory reservation
                for item in items_to_reserve:
                    metrics.track_event("inventory_reserved", user_id, {
                        "item": item['item_name'],
                        "quantity": item['quantity'],
                        "order_code": order.order_code
                    })
                # Track bonus usage if applied
                if bonus_applied > 0:
                    metrics.track_event("payment_bonus_applied", user_id, {
                        "bonus_amount": float(bonus_applied),
                        "order_code": order.order_code
                    })

            cash_instructions = (
                    localize("order.payment.cash.title") + "\n\n" +
                    localize("order.payment.cash.created", code=order.order_code) + "\n\n" +
                    localize("order.payment.cash.items_title") + "\n" + chr(10).join(items_summary) + "\n\n" + localize(
                "order.payment.cash.total", amount=float(total_amount)) + "\n\n" +
                    localize("order.payment.cash.after_confirm") + "\n" +
                    localize("order.payment.cash.payment_to_courier") + "\n\n" +
                    localize("order.payment.cash.important") + "\n" +
                    localize("order.payment.cash.admin_contact")
            )

            # Send payment instructions to user
            payment_text = (
                    f"{cash_instructions}\n\n" +
                    localize("order.payment.order_label", code=order.order_code) + "\n" +
                    localize("order.payment.subtotal_label", amount=total_amount, currency=EnvKeys.PAY_CURRENCY) + "\n"
            )

            if promo_discount > 0:
                payment_text += localize("order.payment.promo_applied_label", code=promo_code,
                                         amount=promo_discount, currency=EnvKeys.PAY_CURRENCY) + "\n"
            if bonus_applied > 0:
                payment_text += localize("order.payment.bonus_applied_label", amount=bonus_applied,
                                         currency=EnvKeys.PAY_CURRENCY) + "\n"
            if promo_discount > 0 or bonus_applied > 0:
                payment_text += localize("order.payment.cash.amount_with_bonus", amount=final_amount,
                                         currency=EnvKeys.PAY_CURRENCY) + "\n\n"
            else:
                payment_text += localize("order.payment.cash.total_label", amount=total_amount,
                                         currency=EnvKeys.PAY_CURRENCY) + "\n\n"

            payment_text += (
                    localize("order.payment.bitcoin.items_title") + "\n"
                                                                    f"{chr(10).join(items_summary)}\n\n" +
                    localize("order.payment.bitcoin.delivery_title") + "\n" +
                    localize("cart.delivery_address", address=customer_info.delivery_address) +
                    localize("cart.delivery_phone", phone=customer_info.phone_number)
            )

            if customer_info.delivery_note:
                payment_text += localize("cart.delivery_note", note=customer_info.delivery_note)

            payment_text += (
                    "\n" + localize("order.info.view_status_hint")
            )

            await message.answer(
                payment_text,
                reply_markup=back("back_to_menu")
            )

            # Notify admin about new cash order
            await notify_admin_new_cash_order(
                message.bot, order.order_code, user_id, username,
                "\n".join(items_summary), total_amount,
                customer_info.delivery_address, customer_info.phone_number,
                customer_info.delivery_note or "", bonus_applied, final_amount
            )

            # Sync customer CSV
            sync_customer_to_csv(user_id, username)

            await state.clear()

        except Exception as e:
            session.rollback()
            logger.error(f"Error creating cash order: {e}")
            await message.answer(
                localize("order.payment.error_general"),
                reply_markup=back("view_cart")
            )
            return


async def notify_admin_new_order(bot, order_code: str, buyer_id: int, buyer_username: str,
                                 items_summary: str, total_amount: Decimal, btc_address: str,
                                 delivery_address: str, phone_number: str, delivery_note: str,
                                 bonus_applied: Decimal = Decimal('0'), final_amount: Decimal = None):
    """
    Send notification to admin about new order
    """
    owner_id = EnvKeys.OWNER_ID

    if not owner_id:
        logger.warning("OWNER_ID not set, cannot send admin notification")
        return

    if final_amount is None:
        final_amount = total_amount

    try:
        admin_text = (
                localize("admin.order.new_bitcoin_order") + "\n\n" +
                localize("admin.order.order_label", code=html.escape(order_code)) + "\n" +
                localize("admin.order.customer_label", username=html.escape(buyer_username), id=buyer_id) + "\n" +
                localize("admin.order.subtotal_label", amount=html.escape(str(total_amount)),
                         currency=html.escape(EnvKeys.PAY_CURRENCY)) + "\n"
        )

        if bonus_applied > 0:
            admin_text += (
                    localize("admin.order.bonus_applied_label", amount=html.escape(str(bonus_applied))) + "\n" +
                    localize("admin.order.amount_to_receive_label", amount=html.escape(str(final_amount)),
                             currency=html.escape(EnvKeys.PAY_CURRENCY)) + "\n\n"
            )
        else:
            admin_text += localize("admin.order.total_label", amount=html.escape(str(total_amount)))

        admin_text += (
                localize("order.payment.bitcoin.items_title") + "\n"
                                                                f"{html.escape(items_summary)}\n\n" +
                localize("order.payment.bitcoin.delivery_title") + "\n" +
                localize("cart.delivery_address", address=html.escape(delivery_address)) +
                localize("cart.delivery_phone", phone=html.escape(phone_number))
        )

        if delivery_note:
            admin_text += localize("cart.delivery_note", note=html.escape(delivery_note))

        admin_text += (
                localize("admin.order.payment_header") +
                localize("admin.order.bitcoin_address_label", address=html.escape(btc_address)) + "\n\n" +
                localize("admin.order.awaiting_payment_status")
        )

        await bot.send_message(
            int(owner_id),
            admin_text
        )

    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")


async def notify_admin_new_cash_order(bot, order_code: str, buyer_id: int, buyer_username: str,
                                      items_summary: str, total_amount: Decimal,
                                      delivery_address: str, phone_number: str, delivery_note: str,
                                      bonus_applied: Decimal = Decimal('0'), final_amount: Decimal = None):
    """
    Send notification to admin about new cash order
    """
    owner_id = EnvKeys.OWNER_ID

    if not owner_id:
        logger.warning("OWNER_ID not set, cannot send admin notification")
        return

    if final_amount is None:
        final_amount = total_amount

    try:
        admin_text = (
                localize("admin.order.new_cash_order") + "\n\n" +
                localize("admin.order.order_label", code=html.escape(order_code)) + "\n" +
                localize("admin.order.customer_label", username=html.escape(buyer_username), id=buyer_id) + "\n" +
                localize("admin.order.payment_method_label", method=localize("admin.order.payment_cash")) + "\n" +
                localize("admin.order.subtotal_label", amount=html.escape(str(total_amount)),
                         currency=html.escape(EnvKeys.PAY_CURRENCY)) + "\n"
        )

        if bonus_applied > 0:
            admin_text += (
                    localize("admin.order.bonus_applied_label", amount=html.escape(str(bonus_applied))) + "\n" +
                    localize("admin.order.amount_to_collect_label", amount=html.escape(str(final_amount)),
                             currency=html.escape(
                                 EnvKeys.PAY_CURRENCY)) + "\n\n"
            )
        else:
            admin_text += localize("admin.order.amount_to_collect_label", amount=html.escape(str(total_amount))) + "\n\n"

        admin_text += (
                localize("order.payment.bitcoin.items_title") + "\n"
                                                                f"{html.escape(items_summary)}\n\n" +
                localize("order.payment.bitcoin.delivery_title") + "\n" +
                localize("cart.delivery_address", address=html.escape(delivery_address)) +
                localize("cart.delivery_phone", phone=html.escape(phone_number))
        )

        if delivery_note:
            admin_text += localize("cart.delivery_note", note=html.escape(delivery_note))

        admin_text += (
                "\n" + localize("admin.order.action_required_title") + "\n" +
                localize("admin.order.use_cli_confirm", code=html.escape(order_code)))

        await bot.send_message(
            int(owner_id),
            admin_text
        )

    except Exception as e:
        logger.error(f"Failed to send admin notification for cash order: {e}")
