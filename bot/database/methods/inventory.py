from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional
from sqlalchemy import and_
from sqlalchemy.orm import Session
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from bot.database.main import Database
from bot.database.models.main import Goods, Order, OrderItem, InventoryLog, CustomerInfo
from bot.database.methods import invalidate_item_cache
from bot.database.methods.cache_utils import safe_create_task
from bot.database.methods.read import get_bot_setting
from bot.export.custom_logging import log_order_cancellation
from bot.export.customer_csv import get_username_by_telegram_id, sync_customer_to_csv
from bot.config import EnvKeys
from bot.i18n import localize
from bot.monitoring import get_metrics

logger = logging.getLogger(__name__)


def log_inventory_change(item_name: str, change_type: str, quantity_change: int,
                          order_id: int = None, admin_id: int = None,
                          comment: str = None, session: Session = None):
    """
    Log inventory change for audit purposes.

    Args:
        item_name: Name of the item
        change_type: Type of change (reserve, release, deduct, add, manual, expired)
        quantity_change: Amount changed (can be negative)
        order_id: Related order ID (optional)
        admin_id: Admin who made the change (optional)
        comment: Additional comment (optional)
        session: Database session (optional, will create if not provided)
    """
    should_commit = session is None
    if session is None:
        session = Database().session()

    try:
        log_entry = InventoryLog(
            item_name=item_name,
            change_type=change_type,
            quantity_change=quantity_change,
            order_id=order_id,
            admin_id=admin_id,
            comment=comment
        )
        session.add(log_entry)

        if should_commit:
            session.commit()
    except Exception as e:
        if should_commit:
            session.rollback()
        raise e
    finally:
        if should_commit:
            session.close()


def reserve_inventory(order_id: int, items: List[Dict[str, any]], payment_method: str = None, session: Session = None) -> Tuple[bool, str]:
    """
    Reserve inventory for an order. Sets reservation timeout based on payment method.

    Args:
        order_id: Order ID to reserve items for
        items: List of dicts with 'item_name' and 'quantity' keys
        payment_method: Payment method ('cash' or 'bitcoin') - determines timeout
        session: Database session (optional)

    Returns:
        Tuple of (success: bool, message: str)
    """
    should_commit = session is None
    if session is None:
        session = Database().session()

    try:
        order = session.query(Order).filter_by(id=order_id).with_for_update().first()
        if not order:
            return False, "Order not found"

        # Determine payment method
        if payment_method is None:
            payment_method = order.payment_method

        # Check and reserve each item
        for item_data in items:
            item_name = item_data['item_name']
            quantity = item_data['quantity']

            # Lock the goods row
            goods = session.query(Goods).filter_by(name=item_name).with_for_update().first()
            if not goods:
                session.rollback()
                return False, f"Item '{item_name}' not found"

            # Check available stock
            available = goods.stock_quantity - goods.reserved_quantity
            if available < quantity:
                session.rollback()
                return False, f"Insufficient stock for '{item_name}'. Available: {available}, Requested: {quantity}"

            # Reserve the stock
            goods.reserved_quantity += quantity

            # Log the reservation
            log_inventory_change(
                item_name=item_name,
                change_type='reserve',
                quantity_change=quantity,
                order_id=order_id,
                comment=f"Reserved for order {order.order_code or order_id} ({payment_method} payment)",
                session=session
            )

            # Invalidate cache for this item
            safe_create_task(invalidate_item_cache(item_name))

        # Set reservation timeout
        timeout_hours = get_bot_setting('cash_order_timeout_hours', default=24, value_type=int)
        order.reserved_until = datetime.now(timezone.utc) + timedelta(hours=timeout_hours)

        order.order_status = 'reserved'

        if should_commit:
            session.commit()

        return True, "Inventory reserved successfully"

    except Exception as e:
        if should_commit:
            session.rollback()
        return False, f"Error reserving inventory: {str(e)}"
    finally:
        if should_commit:
            session.close()


def release_reservation(order_id: int, reason: str = "Order cancelled", session: Session = None) -> Tuple[bool, str]:
    """
    Release reserved inventory back to available stock.
    Called when order is cancelled or expires.

    Args:
        order_id: Order ID to release reservations for
        reason: Reason for release (for logging)
        session: Database session (optional)

    Returns:
        Tuple of (success: bool, message: str)
    """
    should_commit = session is None
    if session is None:
        session = Database().session()

    try:
        order = session.query(Order).filter_by(id=order_id).with_for_update().first()
        if not order:
            return False, "Order not found"

        # Release each item in the order
        for order_item in order.items:
            goods = session.query(Goods).filter_by(name=order_item.item_name).with_for_update().first()
            if goods:
                # Release the reservation
                goods.reserved_quantity -= order_item.quantity

                # Ensure reserved_quantity doesn't go negative
                if goods.reserved_quantity < 0:
                    goods.reserved_quantity = 0

                # Log the release
                log_inventory_change(
                    item_name=order_item.item_name,
                    change_type='release',
                    quantity_change=-order_item.quantity,  # Negative because we're reducing reserved
                    order_id=order_id,
                    comment=f"{reason} - {order.order_code or order_id}",
                    session=session
                )

                # Invalidate cache for this item
                safe_create_task(invalidate_item_cache(order_item.item_name))

        # Clear reservation timeout
        order.reserved_until = None

        if should_commit:
            session.commit()

        # Track inventory release metrics
        metrics = get_metrics()
        if metrics:
            for order_item in order.items:
                metrics.track_event("inventory_released", None, {
                    "item": order_item.item_name,
                    "quantity": order_item.quantity,
                    "order_code": order.order_code,
                    "reason": reason
                })

        return True, "Reservation released successfully"

    except Exception as e:
        if should_commit:
            session.rollback()
        return False, f"Error releasing reservation: {str(e)}"
    finally:
        if should_commit:
            session.close()


def deduct_inventory(order_id: int, admin_id: int = None, session: Session = None) -> Tuple[bool, str]:
    """
    Deduct inventory from stock when order is confirmed by admin.
    This is the ACTUAL inventory reduction (not just reservation).

    Args:
        order_id: Order ID to deduct inventory for
        admin_id: ID of admin confirming the order
        session: Database session (optional)

    Returns:
        Tuple of (success: bool, message: str)
    """
    should_commit = session is None
    if session is None:
        session = Database().session()

    try:
        order = session.query(Order).filter_by(id=order_id).with_for_update().first()
        if not order:
            return False, "Order not found"

        # Deduct each item from stock
        for order_item in order.items:
            goods = session.query(Goods).filter_by(name=order_item.item_name).with_for_update().first()
            if not goods:
                session.rollback()
                return False, f"Item '{order_item.item_name}' not found"

            # Deduct from both stock_quantity and reserved_quantity
            goods.stock_quantity -= order_item.quantity
            goods.reserved_quantity -= order_item.quantity

            # Safety check
            if goods.stock_quantity < 0:
                session.rollback()
                return False, f"Stock would go negative for '{order_item.item_name}'"
            if goods.reserved_quantity < 0:
                goods.reserved_quantity = 0  # Fix if somehow went negative

            # Log the deduction
            log_inventory_change(
                item_name=order_item.item_name,
                change_type='deduct',
                quantity_change=-order_item.quantity,
                order_id=order_id,
                admin_id=admin_id,
                comment=f"Order confirmed: {order.order_code or order_id}",
                session=session
            )

            # Invalidate cache for this item
            safe_create_task(invalidate_item_cache(order_item.item_name))

        # Clear reservation timeout since it's now confirmed
        order.reserved_until = None

        if should_commit:
            session.commit()

        # Track inventory deduction metrics
        metrics = get_metrics()
        if metrics:
            for order_item in order.items:
                metrics.track_event("inventory_deducted", None, {
                    "item": order_item.item_name,
                    "quantity": order_item.quantity,
                    "order_code": order.order_code,
                    "admin_id": admin_id
                })

        return True, "Inventory deducted successfully"

    except Exception as e:
        if should_commit:
            session.rollback()
        return False, f"Error deducting inventory: {str(e)}"
    finally:
        if should_commit:
            session.close()


def add_inventory(item_name: str, quantity: int, admin_id: int = None,
                 comment: str = None, session: Session = None) -> Tuple[bool, str]:
    """
    Add inventory to stock (e.g., restocking).

    Args:
        item_name: Name of the item
        quantity: Amount to add
        admin_id: ID of admin adding stock
        comment: Reason for adding (optional)
        session: Database session (optional)

    Returns:
        Tuple of (success: bool, message: str)
    """
    should_commit = session is None
    if session is None:
        session = Database().session()

    try:
        goods = session.query(Goods).filter_by(name=item_name).with_for_update().first()
        if not goods:
            return False, f"Item '{item_name}' not found"

        # Add to stock
        goods.stock_quantity += quantity

        # Log the addition
        log_inventory_change(
            item_name=item_name,
            change_type='add',
            quantity_change=quantity,
            admin_id=admin_id,
            comment=comment or "Stock added",
            session=session
        )

        # Invalidate cache for this item
        safe_create_task(invalidate_item_cache(item_name))

        if should_commit:
            session.commit()

        return True, f"Added {quantity} units to {item_name}"

    except Exception as e:
        if should_commit:
            session.rollback()
        return False, f"Error adding inventory: {str(e)}"
    finally:
        if should_commit:
            session.close()


def get_inventory_stats(item_name: str) -> Optional[Dict[str, int]]:
    """
    Get current inventory statistics for an item.

    Args:
        item_name: Name of the item

    Returns:
        Dict with 'stock', 'reserved', 'available' keys, or None if item not found
    """
    with Database().session() as session:
        goods = session.query(Goods).filter_by(name=item_name).first()
        if not goods:
            return None

        return {
            'stock': goods.stock_quantity,
            'reserved': goods.reserved_quantity,
            'available': goods.available_quantity
        }


async def cleanup_expired_reservations() -> Tuple[int, List[str]]:
    """
    Find and release expired reservations.
    Called by background task every 1-2 minutes.

    Returns:
        Tuple of (count: int, order_codes: List[str])
    """
    with Database().session() as session:
        # Find expired orders
        now = datetime.now(timezone.utc)
        expired_orders = session.query(Order).filter(
            and_(
                Order.order_status == 'reserved',
                Order.reserved_until < now
            )
        ).all()

        count = 0
        order_codes = []

        for order in expired_orders:
            # Release reservation
            success, message = release_reservation(
                order.id,
                reason="Reservation timeout expired",
                session=session
            )

            if success:
                # Mark order as expired
                order.order_status = 'expired'

                # Refund referral bonus if it was applied
                if order.bonus_applied and order.bonus_applied > 0:
                    customer_info = session.query(CustomerInfo).filter_by(
                        telegram_id=order.buyer_id
                    ).first()

                    if customer_info:
                        old_bonus_balance = customer_info.bonus_balance
                        customer_info.bonus_balance += order.bonus_applied
                        new_bonus_balance = customer_info.bonus_balance

                        # Get buyer username for CSV sync
                        buyer_username = get_username_by_telegram_id(order.buyer_id) or f"user_{order.buyer_id}"

                        # Sync to CSV file
                        sync_customer_to_csv(order.buyer_id, buyer_username)

                        # Send notification to customer about bonus refund
                        try:
                            bot = Bot(
                                token=EnvKeys.TOKEN,
                                default=DefaultBotProperties(parse_mode="HTML")
                            )

                            try:
                                notification_text = localize(
                                    "order.expired.bonus_refund_notification",
                                    code=order.order_code,
                                    bonus=order.bonus_applied,
                                    balance=new_bonus_balance,
                                )

                                await bot.send_message(order.buyer_id, notification_text)
                                logger.info(f"Bonus refund notification sent for expired order {order.order_code} (buyer: {order.buyer_id})")
                            finally:
                                await bot.session.close()

                        except Exception as e:
                            logger.warning(f"Failed to send bonus refund notification for order {order.order_code}: {e}")
                            # Continue execution even if notification fails

                        logger.info(
                            f"Refunded bonus {order.bonus_applied} to buyer {order.buyer_id} "
                            f"(order: {order.order_code}, old balance: {old_bonus_balance}, "
                            f"new balance: {new_bonus_balance})"
                        )

                # Get order items for logging
                order_items = session.query(OrderItem).filter_by(order_id=order.id).all()
                if order_items:
                    items_list = [f"{item.item_name} x {item.quantity}" for item in order_items]
                    items_summary = ", ".join(items_list)
                else:
                    items_summary = "N/A"

                # Log order cancellation
                buyer_username = get_username_by_telegram_id(order.buyer_id) or f"user_{order.buyer_id}"
                log_order_cancellation(
                    order_id=order.id,
                    buyer_id=order.buyer_id,
                    buyer_username=buyer_username,
                    items_summary=items_summary,
                    total=float(order.total_price),
                    reason="Reservation expired",
                    order_code=order.order_code
                )

                count += 1
                order_codes.append(order.order_code or str(order.id))

        session.commit()

        return count, order_codes
