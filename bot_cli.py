import argparse
import sys
import os
import asyncio
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta, timezone

# Add bot directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env BEFORE importing any bot.* module: EnvKeys validates required vars at
# import time, so the CLI must populate the environment first.
from dotenv import load_dotenv

load_dotenv(encoding='utf-8')

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from bot.database.main import Database
from bot.database.models.main import (
    User, Order, CustomerInfo, BotSettings,
    ReferenceCode, BitcoinAddress, Goods,
    ReferralEarnings, OrderItem
)
from bot.database.methods.update import ban_user, unban_user
from bot.database.methods.inventory import deduct_inventory, release_reservation, add_inventory, reserve_inventory
from bot.database.methods.read import get_reference_bonus_percent
from bot.database.methods.audit import log_audit, get_recent_audit_logs
from bot.utils.money import format_price
from bot.referrals.codes import create_reference_code, deactivate_reference_code
from bot.payments.bitcoin import add_bitcoin_address, add_bitcoin_addresses_bulk, get_bitcoin_address_stats
from bot.export.customer_csv import (
    update_customer_spendings,
    sync_all_customers_to_csv,
    export_customers_csv,
    get_username_by_telegram_id,
    sync_customer_to_csv
)
from bot.export.custom_logging import (
    log_order_completion,
    log_order_cancellation,
    log_inventory_update
)
from bot.config import timezone as tz_config, EnvKeys

from bot.payments.notifications import (
    notify_order_confirmed,
    notify_order_delivered,
    notify_order_modified
)


def get_admin_user_id():
    """
    Get admin user ID from environment or database

    Returns:
        int: Admin user telegram ID or None if not found
    """
    owner_id = os.getenv('OWNER_ID')
    if owner_id:
        return int(owner_id)

    # Get from database
    with Database().session() as session:
        from bot.database.models.main import User, Role
        admin_user = session.query(User).join(Role).filter(
            Role.name.in_(['ADMIN', 'OWNER'])
        ).first()

        if admin_user:
            return admin_user.telegram_id

    return None


async def get_telegram_username(telegram_id: int) -> str:
    """
    Get Telegram username using Bot API

    Args:
        telegram_id: Telegram user ID

    Returns:
        Username (with @ prefix if available) or fallback user_{telegram_id}
    """
    try:
        bot = Bot(
            token=EnvKeys.TOKEN,
            default=DefaultBotProperties(
                parse_mode="HTML",
                link_preview_is_disabled=False,
                protect_content=False,
            ),
        )

        try:
            chat = await bot.get_chat(telegram_id)
            if chat.username:
                return chat.username
        finally:
            await bot.session.close()

    except Exception as e:
        # If we can't get username from Telegram, use fallback
        pass

    return f"user_{telegram_id}"


async def complete_order_by_code(order_code: str):
    """
    Mark an order as completed using order code

    Args:
        order_code: Unique 6-character order code (e.g., ECBDJI)
    """
    with Database().session() as session:
        # Find order by code
        order = session.query(Order).filter_by(order_code=order_code).first()

        if not order:
            print(f"❌ Order not found with code: {order_code}")
            print("   Make sure the order code is correct")
            return

        # Check if already completed
        if order.order_status == 'completed':
            print(f"⚠️  Order {order_code} is already completed")
            return

        # Check if canceled
        if order.order_status == 'canceled':
            print(f"❌ Cannot complete canceled order {order_code}")
            return

        # Get buyer information - username from Telegram API
        buyer = session.query(User).filter_by(telegram_id=order.buyer_id).first()

        # Get username from Telegram API
        buyer_username = await get_telegram_username(order.buyer_id)

        # Deduct inventory from stock (actual reduction)
        success, deduct_message = deduct_inventory(order.id, admin_id=int(os.getenv('OWNER_ID', 0)), session=session)
        if not success:
            print(f"❌ Failed to deduct inventory: {deduct_message}")
            print("   Order not completed")
            return

        # Mark order as completed
        order.order_status = 'completed'
        order.completed_at = datetime.now(timezone.utc)

        log_audit(
            "order_completed",
            user_id=int(os.getenv('OWNER_ID', 0)) or None,
            resource_type="Order", resource_id=order_code,
            details=f"marked completed; total={order.total_price}",
            session=session,
        )

        # Update customer spendings
        update_customer_spendings(
            order.buyer_id,
            buyer_username,
            order.total_price
        )

        # Process referral bonus if applicable
        referral_bonus_amount = Decimal('0')
        referral_percent = get_reference_bonus_percent()
        if buyer and buyer.referral_id and referral_percent > 0:
            referral_bonus_amount = (order.total_price * referral_percent) / Decimal('100')

            # Get referrer
            referrer = session.query(User).filter_by(
                telegram_id=buyer.referral_id
            ).with_for_update().first()

            if referrer:
                # Create referral earnings record
                earning = ReferralEarnings(
                    referrer_id=buyer.referral_id,
                    referral_id=buyer.telegram_id,
                    amount=referral_bonus_amount,
                    original_amount=order.total_price
                )
                session.add(earning)

                # Update referrer's bonus balance in CustomerInfo
                referrer_customer_info = session.query(CustomerInfo).filter_by(
                    telegram_id=buyer.referral_id
                ).first()

                if referrer_customer_info:
                    referrer_customer_info.bonus_balance += referral_bonus_amount
                    total_bonus_balance = referrer_customer_info.bonus_balance
                else:
                    total_bonus_balance = referral_bonus_amount

                # Send notification to referrer about the bonus
                try:
                    bot = Bot(
                        token=EnvKeys.TOKEN,
                        default=DefaultBotProperties(parse_mode="HTML")
                    )

                    try:
                        notification_text = (
                            f"🎉 <b>Referral Bonus Received!</b>\n\n"
                            f"Your referral completed an order.\n\n"
                            f"💰 <b>Bonus Amount: {format_price(referral_bonus_amount)}</b>\n"
                            f"📊 Total Bonus Balance: <b>{format_price(total_bonus_balance)}</b>\n\n"
                            f"Order Total: {format_price(order.total_price)}\n"
                            f"Order Code: {order.order_code}\n\n"
                            f"💡 You can use this bonus to reduce payment on your next order!"
                        )

                        await bot.send_message(
                            buyer.referral_id,
                            notification_text
                        )
                    finally:
                        await bot.session.close()

                except Exception as e:
                    print(f"⚠️  Failed to send referral bonus notification: {e}")
                    # Continue execution even if notification fails

                print(f"💰 Referral bonus: {format_price(referral_bonus_amount)} credited to referrer (ID: {buyer.referral_id})")

        session.commit()

        # Log completion - get all order items
        from bot.database.models.main import OrderItem
        order_items = session.query(OrderItem).filter_by(order_id=order.id).all()

        # Build items summary: "item1 x 2, item2 x 1"
        if order_items:
            items_list = [f"{item.item_name} x {item.quantity}" for item in order_items]
            items_summary = ", ".join(items_list)
        else:
            items_summary = "N/A"

        log_order_completion(
            order_id=order.id,
            buyer_id=order.buyer_id,
            buyer_username=buyer_username,
            items_summary=items_summary,
            total=float(order.total_price),
            completed_by=int(os.getenv('OWNER_ID', 0)),
            completed_by_username='admin_cli',
            order_code=order.order_code
        )

        print(f"✅ Order {order_code} completed successfully")
        print(f"   Customer: @{buyer_username} (ID: {order.buyer_id})")
        print(f"   Total: {format_price(order.total_price)}")
        print(f"   Payment Method: {order.payment_method}")
        if referral_bonus_amount > 0:
            print(f"   Referral Bonus: {format_price(referral_bonus_amount)}")


async def cancel_order_by_code(order_code: str):
    """
    Cancel an order using order code

    Args:
        order_code: Unique 6-character order code (e.g., ECBDJI)
    """
    with Database().session() as session:
        # Find order by code
        order = session.query(Order).filter_by(order_code=order_code).first()

        if not order:
            print(f"❌ Order not found with code: {order_code}")
            print("   Make sure the order code is correct")
            return

        # Check if already canceled
        if order.order_status == 'canceled':
            print(f"⚠️  Order {order_code} is already canceled")
            return

        # Check if already completed
        if order.order_status == 'completed':
            print(f"❌ Cannot cancel completed order {order_code}")
            print("   Completed orders cannot be canceled")
            return

        # Get buyer information - try to get real username from CSV
        buyer = session.query(User).filter_by(telegram_id=order.buyer_id).first()

        # Try to get username from CSV, fallback to user_{id}
        buyer_username = get_username_by_telegram_id(order.buyer_id) or f"user_{order.buyer_id}"

        # Release inventory reservation
        success, release_message = release_reservation(order.id, reason="Order canceled by admin", session=session)
        if not success:
            print(f"⚠️  Warning: Failed to release reservation: {release_message}")
            # Continue with cancellation anyway

        # Mark order as canceled
        order.order_status = 'canceled'

        log_audit(
            "order_canceled",
            user_id=int(os.getenv('OWNER_ID', 0)) or None,
            resource_type="Order", resource_id=order_code,
            details=f"canceled by admin; total={order.total_price}",
            session=session,
        )

        # Refund referral bonus if it was applied
        bonus_refunded = False
        if order.bonus_applied and order.bonus_applied > 0:
            customer_info = session.query(CustomerInfo).filter_by(
                telegram_id=order.buyer_id
            ).first()

            if customer_info:
                old_bonus_balance = customer_info.bonus_balance
                customer_info.bonus_balance += order.bonus_applied
                new_bonus_balance = customer_info.bonus_balance
                bonus_refunded = True

                print(f"💰 Refunded bonus: {format_price(order.bonus_applied)}")
                print(f"   Previous bonus balance: {format_price(old_bonus_balance)}")
                print(f"   New bonus balance: {format_price(new_bonus_balance)}")
                print(f"   Buyer ID: {order.buyer_id}")
                print(f"   Order code: {order.order_code}")

                # Sync to CSV file
                sync_customer_to_csv(order.buyer_id, buyer_username)

                # Send notification to customer about bonus refund
                try:
                    bot = Bot(
                        token=EnvKeys.TOKEN,
                        default=DefaultBotProperties(parse_mode="HTML")
                    )

                    try:
                        notification_text = (
                            f"ℹ️ <b>Order Canceled</b>\n\n"
                            f"Your order <b>{order.order_code}</b> has been canceled by admin.\n\n"
                            f"💰 <b>Bonus Refund: {format_price(order.bonus_applied)}</b>\n"
                            f"📊 New Bonus Balance: <b>{format_price(new_bonus_balance)}</b>\n\n"
                            f"Your referral bonus has been returned to your account.\n"
                            f"You can use it for your next order!"
                        )

                        await bot.send_message(order.buyer_id, notification_text)
                        print(f"📧 Bonus refund notification sent to customer")
                    finally:
                        await bot.session.close()

                except Exception as e:
                    print(f"⚠️  Failed to send bonus refund notification: {e}")
                    # Continue execution even if notification fails

        # Get order items for logging
        from bot.database.models.main import OrderItem
        order_items = session.query(OrderItem).filter_by(order_id=order.id).all()
        if order_items:
            items_list = [f"{item.item_name} x {item.quantity}" for item in order_items]
            items_summary = ", ".join(items_list)
        else:
            items_summary = "N/A"

        # Get admin user ID
        admin_id = get_admin_user_id()
        if not admin_id:
            admin_id = int(os.getenv('OWNER_ID', 0))

        # Log order cancellation
        log_order_cancellation(
            order_id=order.id,
            buyer_id=order.buyer_id,
            buyer_username=buyer_username,
            items_summary=items_summary,
            total=float(order.total_price),
            reason="Canceled by admin",
            canceled_by=admin_id,
            canceled_by_username='admin_cli',
            order_code=order.order_code
        )

        session.commit()

        print(f"✅ Order {order_code} canceled successfully")
        print(f"   Customer: @{buyer_username} (ID: {order.buyer_id})")
        print(f"   Total: {format_price(order.total_price)}")
        print(f"   Payment Method: {order.payment_method}")


async def confirm_order_with_delivery_time(order_code: str, delivery_time_str: str):
    """
    Confirm an order and set delivery time

    Args:
        order_code: Unique 6-character order code
        delivery_time_str: Delivery time in format "YYYY-MM-DD HH:MM"
    """
    with Database().session() as session:
        # Find order by code
        order = session.query(Order).filter_by(order_code=order_code).first()

        if not order:
            print(f"❌ Order not found with code: {order_code}")
            return

        # Check if already delivered
        if order.order_status == 'delivered':
            print(f"⚠️  Order {order_code} is already delivered")
            return

        # Check if cancelled
        if order.order_status in ['cancelled', 'canceled', 'expired']:
            print(f"❌ Cannot confirm cancelled/expired order {order_code}")
            return

        # Parse delivery time
        try:
            delivery_time = datetime.strptime(delivery_time_str, "%Y-%m-%d %H:%M")
            # Make it timezone-aware (UTC)
            delivery_time = delivery_time.replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"❌ Invalid delivery time format. Use: YYYY-MM-DD HH:MM")
            print(f"   Example: 2025-11-16 18:45")
            return

        # Update order
        old_status = order.order_status
        order.order_status = 'confirmed'
        order.delivery_time = delivery_time

        # Extend reservation if needed (in case it's about to expire)
        if order.reserved_until and order.reserved_until < datetime.now(timezone.utc) + timedelta(hours=1):
            order.reserved_until = delivery_time + timedelta(hours=1)

        log_audit(
            "order_confirmed",
            user_id=int(os.getenv('OWNER_ID', 0)) or None,
            resource_type="Order", resource_id=order_code,
            details=f"{old_status} -> confirmed; delivery_time={delivery_time_str}",
            session=session,
        )

        session.commit()

        # Get order items for notification
        order_items = session.query(OrderItem).filter_by(order_id=order.id).all()

        # Send notification to customer
        try:
            success = await notify_order_confirmed(
                order=order,
                items=order_items,
                delivery_time=delivery_time
            )

            if success:
                print(f"[OK] Notification sent to customer")
            else:
                print(f"[WARNING] Failed to send notification to customer")

        except Exception as e:
            print(f"[WARNING] Error sending notification: {str(e)[:100]}")

        print(f"[SUCCESS] Order {order_code} confirmed")
        print(f"   Status: {old_status} -> confirmed")
        print(f"   Delivery time: {delivery_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Customer ID: {order.buyer_id}")
        print(f"   Total: {format_price(order.total_price)}")


async def mark_order_delivered(order_code: str):
    """
    Mark an order as delivered and deduct inventory

    Args:
        order_code: Unique 6-character order code
    """
    with Database().session() as session:
        # Find order by code
        order = session.query(Order).filter_by(order_code=order_code).first()

        if not order:
            print(f"❌ Order not found with code: {order_code}")
            return

        # Check if already delivered
        if order.order_status == 'delivered':
            print(f"⚠️  Order {order_code} is already delivered")
            return

        # Check if cancelled
        if order.order_status in ['cancelled', 'canceled', 'expired']:
            print(f"❌ Cannot deliver cancelled/expired order {order_code}")
            return

        # Get buyer information
        buyer = session.query(User).filter_by(telegram_id=order.buyer_id).first()
        buyer_username = await get_telegram_username(order.buyer_id)

        # Deduct inventory from stock (actual reduction)
        success, deduct_message = deduct_inventory(
            order.id,
            admin_id=int(os.getenv('OWNER_ID', 0)),
            session=session
        )

        if not success:
            print(f"❌ Failed to deduct inventory: {deduct_message}")
            print("   Order not marked as delivered")
            return

        # Mark order as delivered
        old_status = order.order_status
        order.order_status = 'delivered'
        order.completed_at = datetime.now(timezone.utc)

        log_audit(
            "order_delivered",
            user_id=int(os.getenv('OWNER_ID', 0)) or None,
            resource_type="Order", resource_id=order_code,
            details=f"{old_status} -> delivered; total={order.total_price}",
            session=session,
        )

        # Update customer spendings
        update_customer_spendings(
            order.buyer_id,
            buyer_username,
            order.total_price
        )

        # Process referral bonus if applicable
        referral_bonus_amount = Decimal('0')
        referral_percent = get_reference_bonus_percent()

        if buyer and buyer.referral_id and referral_percent > 0:
            referral_bonus_amount = (order.total_price * referral_percent) / Decimal('100')

            # Get referrer
            referrer = session.query(User).filter_by(
                telegram_id=buyer.referral_id
            ).with_for_update().first()

            if referrer:
                # Create referral earnings record
                earning = ReferralEarnings(
                    referrer_id=buyer.referral_id,
                    referral_id=buyer.telegram_id,
                    amount=referral_bonus_amount,
                    original_amount=order.total_price
                )
                session.add(earning)

                # Update referrer's bonus balance in CustomerInfo
                referrer_customer_info = session.query(CustomerInfo).filter_by(
                    telegram_id=buyer.referral_id
                ).first()

                if referrer_customer_info:
                    referrer_customer_info.bonus_balance += referral_bonus_amount
                    total_bonus_balance = referrer_customer_info.bonus_balance
                else:
                    total_bonus_balance = referral_bonus_amount

                # Send notification to referrer about the bonus
                try:
                    bot = Bot(
                        token=EnvKeys.TOKEN,
                        default=DefaultBotProperties(parse_mode="HTML")
                    )

                    try:
                        notification_text = (
                            f"🎉 <b>Referral Bonus Received!</b>\n\n"
                            f"Your referral completed an order.\n\n"
                            f"💰 <b>Bonus Amount: {format_price(referral_bonus_amount)}</b>\n"
                            f"📊 Total Bonus Balance: <b>{format_price(total_bonus_balance)}</b>\n\n"
                            f"Order Total: {format_price(order.total_price)}\n"
                            f"Order Code: {order.order_code}\n\n"
                            f"💡 You can use this bonus to reduce payment on your next order!"
                        )

                        await bot.send_message(buyer.referral_id, notification_text)
                    finally:
                        await bot.session.close()

                except Exception as e:
                    print(f"⚠️  Failed to send referral bonus notification: {e}")

                print(f"💰 Referral bonus: {format_price(referral_bonus_amount)} credited to referrer (ID: {buyer.referral_id})")

        session.commit()

        # Log completion
        order_items = session.query(OrderItem).filter_by(order_id=order.id).all()

        if order_items:
            items_list = [f"{item.item_name} x {item.quantity}" for item in order_items]
            items_summary = ", ".join(items_list)
        else:
            items_summary = "N/A"

        log_order_completion(
            order_id=order.id,
            buyer_id=order.buyer_id,
            buyer_username=buyer_username,
            items_summary=items_summary,
            total=float(order.total_price),
            completed_by=int(os.getenv('OWNER_ID', 0)),
            completed_by_username='admin_cli',
            order_code=order.order_code
        )

        # Send delivery notification to customer
        try:
            success = await notify_order_delivered(order=order)

            if success:
                print(f"📧 Delivery notification sent to customer")
            else:
                print(f"⚠️  Failed to send delivery notification")

        except Exception as e:
            print(f"⚠️  Error sending notification: {e}")

        print(f"✅ Order {order_code} marked as delivered")
        print(f"   Status: {old_status} → delivered")
        print(f"   Customer: @{buyer_username} (ID: {order.buyer_id})")
        print(f"   Total: {format_price(order.total_price)}")
        print(f"   Payment Method: {order.payment_method}")
        if referral_bonus_amount > 0:
            print(f"   Referral Bonus: {format_price(referral_bonus_amount)}")


async def add_item_to_order(order_code: str, item_name: str, quantity: int, notify: bool = False):
    """
    Add items to an existing order

    Args:
        order_code: Unique 6-character order code
        item_name: Name of the item to add
        quantity: Quantity to add
        notify: Whether to notify customer
    """
    with Database().session() as session:
        # Find order
        order = session.query(Order).filter_by(order_code=order_code).first()

        if not order:
            print(f"❌ Order not found with code: {order_code}")
            return

        # Find goods
        goods = session.query(Goods).filter_by(name=item_name).first()

        if not goods:
            print(f"❌ Item '{item_name}' not found")
            return

        # Check if item already in order
        existing_item = session.query(OrderItem).filter_by(
            order_id=order.id,
            item_name=item_name
        ).first()

        if existing_item:
            existing_item.quantity += quantity
            print(f"   Updated existing item quantity: {existing_item.quantity - quantity} → {existing_item.quantity}")
        else:
            new_item = OrderItem(
                order_id=order.id,
                item_name=item_name,
                price=goods.price,
                quantity=quantity
            )
            session.add(new_item)
            print(f"   Added new item to order")

        if order.order_status != 'delivered':
            # Reserve additional inventory
            items_to_reserve = [{'item_name': item_name, 'quantity': quantity}]
            success, message = reserve_inventory(
                order.id,
                items_to_reserve,
                payment_method=order.payment_method,
                session=session
            )

            if not success:
                session.rollback()
                print(f"❌ Failed to reserve inventory: {message}")
                return

        # Recalculate order total
        order_items = session.query(OrderItem).filter_by(order_id=order.id).all()
        order.total_price = sum(item.price * item.quantity for item in order_items)

        session.commit()

        # Send notification if requested
        if notify:
            changes_desc = f"+ {item_name} x {quantity} ({format_price(goods.price * quantity)})"
            try:
                await notify_order_modified(
                    order=order,
                    changes_description=changes_desc
                )
                print(f"📧 Modification notification sent to customer")
            except Exception as e:
                print(f"⚠️  Failed to send notification: {e}")

        print(f"✅ Added {quantity}x {item_name} to order {order_code}")
        print(f"   Item price: {format_price(goods.price)}")
        print(f"   New order total: {format_price(order.total_price)}")


async def remove_item_from_order(order_code: str, item_name: str, quantity: int, notify: bool = False):
    """
    Remove items from an existing order

    Args:
        order_code: Unique 6-character order code
        item_name: Name of the item to remove
        quantity: Quantity to remove
        notify: Whether to notify customer
    """
    with Database().session() as session:
        # Find order
        order = session.query(Order).filter_by(order_code=order_code).first()

        if not order:
            print(f"❌ Order not found with code: {order_code}")
            return

        # Find item in order
        order_item = session.query(OrderItem).filter_by(
            order_id=order.id,
            item_name=item_name
        ).first()

        if not order_item:
            print(f"❌ Item '{item_name}' not found in order")
            return

        if order_item.quantity < quantity:
            print(f"❌ Cannot remove {quantity} items. Order only has {order_item.quantity}")
            return

        old_quantity = order_item.quantity
        removed_value = order_item.price * quantity

        # Update or remove item
        if order_item.quantity == quantity:
            session.delete(order_item)
            print(f"   Removed item completely from order")
        else:
            order_item.quantity -= quantity
            print(f"   Updated item quantity: {old_quantity} → {order_item.quantity}")

        # Release inventory reservation
        from bot.database.models.main import Goods
        goods = session.query(Goods).filter_by(name=item_name).with_for_update().first()

        if goods:
            goods.reserved_quantity -= quantity
            print(f"   Released {quantity} units back to inventory")

        # Recalculate order total
        order_items = session.query(OrderItem).filter_by(order_id=order.id).all()
        order.total_price = sum(item.price * item.quantity for item in order_items)

        session.commit()

        # Send notification if requested
        if notify:
            changes_desc = f"- {item_name} x {quantity} (-{format_price(removed_value)})"
            try:
                await notify_order_modified(
                    order=order,
                    changes_description=changes_desc
                )
                print(f"📧 Modification notification sent to customer")
            except Exception as e:
                print(f"⚠️  Failed to send notification: {e}")

        print(f"✅ Removed {quantity}x {item_name} from order {order_code}")
        print(f"   Value removed: {format_price(removed_value)}")
        print(f"   New order total: {format_price(order.total_price)}")


async def update_delivery_time(order_code: str, delivery_time_str: str, notify: bool = False):
    """
    Update delivery time for an order

    Args:
        order_code: Unique 6-character order code
        delivery_time_str: New delivery time in format "YYYY-MM-DD HH:MM"
        notify: Whether to notify customer
    """
    with Database().session() as session:
        # Find order
        order = session.query(Order).filter_by(order_code=order_code).first()

        if not order:
            print(f"❌ Order not found with code: {order_code}")
            return

        if order.order_status == 'delivered':
            print(f"⚠️  Order {order_code} is already delivered")
            return

        # Parse delivery time
        try:
            delivery_time = datetime.strptime(delivery_time_str, "%Y-%m-%d %H:%M")
            # Make it timezone-aware (UTC)
            delivery_time = delivery_time.replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"❌ Invalid delivery time format. Use: YYYY-MM-DD HH:MM")
            print(f"   Example: 2025-11-16 18:45")
            return

        old_time = order.delivery_time.strftime('%Y-%m-%d %H:%M') if order.delivery_time else "Not set"

        # Update delivery time
        order.delivery_time = delivery_time

        # Extend reservation if needed
        if order.reserved_until and order.reserved_until < delivery_time:
            order.reserved_until = delivery_time + timedelta(hours=1)

        session.commit()

        # Send notification if requested
        if notify:
            changes_desc = f"Delivery time updated:\n  {old_time} → {delivery_time.strftime('%Y-%m-%d %H:%M')}"
            try:
                await notify_order_modified(
                    order=order,
                    changes_description=changes_desc
                )
                print(f"📧 Update notification sent to customer")
            except Exception as e:
                print(f"⚠️  Failed to send notification: {e}")

        print(f"✅ Updated delivery time for order {order_code}")
        print(f"   Old time: {old_time}")
        print(f"   New time: {delivery_time.strftime('%Y-%m-%d %H:%M')}")


def create_refcode(args):
    """Create a new reference code"""
    try:
        # Get creator user ID
        if hasattr(args, 'created_by') and args.created_by:
            created_by = args.created_by
        else:
            created_by = get_admin_user_id()
            if not created_by:
                print("❌ Error: No admin user found in database.")
                print("   Either:")
                print("   1. Set OWNER_ID environment variable")
                print("   2. Use --created-by USER_ID")
                print("   3. Ensure at least one admin user exists in database")
                return
            print(f"ℹ️  Using admin user ID: {created_by}")

        expires_in_hours = args.expires_hours if args.expires_hours > 0 else None
        max_uses = args.max_uses if args.max_uses > 0 else None

        code = create_reference_code(
            created_by=created_by,
            created_by_username='admin_cli',
            is_admin_code=True,
            expires_in_hours=expires_in_hours,
            max_uses=max_uses,
            note=args.note
        )

        log_audit(
            "refcode_created", user_id=created_by,
            resource_type="ReferenceCode", resource_id=code,
            details=f"expires_hours={expires_in_hours}; max_uses={max_uses}; note={args.note or ''}",
        )

        print(f"✅ Reference code created: {code}")
        if expires_in_hours:
            print(f"   Expires in: {expires_in_hours} hours")
        else:
            print(f"   Expires: Never")

        if max_uses:
            print(f"   Max uses: {max_uses}")
        else:
            print(f"   Max uses: Unlimited")

        if args.note:
            print(f"   Note: {args.note}")

    except Exception as e:
        print(f"❌ Error creating reference code: {e}")


def disable_refcode(args):
    """Disable a reference code"""
    # Get admin user ID
    admin_id = get_admin_user_id()
    if not admin_id:
        print("❌ Error: No admin user found. Set OWNER_ID environment variable.")
        return

    success = deactivate_reference_code(
        code=args.code,
        deactivated_by=admin_id,
        deactivated_by_username='admin_cli',
        reason=args.reason or "Disabled via CLI"
    )

    if success:
        log_audit(
            "refcode_disabled", level="WARNING", user_id=admin_id,
            resource_type="ReferenceCode", resource_id=args.code,
            details=f"reason={args.reason or 'Disabled via CLI'}",
        )
        print(f"✅ Reference code {args.code} has been disabled")
    else:
        print(f"❌ Reference code {args.code} not found")


def list_refcodes(args):
    """List all reference codes"""
    with Database().session() as session:
        query = session.query(ReferenceCode)

        if args.active_only:
            query = query.filter_by(is_active=True)

        codes = query.order_by(ReferenceCode.created_at.desc()).all()

        if not codes:
            print("No reference codes found")
            return

        print(f"\n{'Code':<10} {'Type':<6} {'Created':<20} {'Expires':<20} {'Uses':<10} {'Active':<7}")
        print("-" * 80)

        for code in codes:
            code_type = "ADMIN" if code.is_admin_code else "USER"
            created = code.created_at.strftime('%Y-%m-%d %H:%M')
            expires = code.expires_at.strftime('%Y-%m-%d %H:%M') if code.expires_at else "Never"
            max_uses = str(code.max_uses) if code.max_uses else "∞"
            uses = f"{code.current_uses}/{max_uses}"
            active = "Yes" if code.is_active else "No"

            print(f"{code.code:<10} {code_type:<6} {created:<20} {expires:<20} {uses:<10} {active:<7}")

        print(f"\nTotal: {len(codes)} reference codes")


def add_btc_address(args):
    """Add Bitcoin address(es)"""
    if args.file:
        # Load from file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {args.file}")
            return

        with open(file_path, 'r') as f:
            addresses = [line.strip() for line in f if line.strip()]

        count = add_bitcoin_addresses_bulk(addresses)
        print(f"✅ Added {count} Bitcoin address(es)")

    elif args.address:
        # Add single address
        success = add_bitcoin_address(args.address)
        if success:
            print(f"✅ Bitcoin address added: {args.address}")
        else:
            print(f"❌ Bitcoin address already exists: {args.address}")


def list_btc_addresses(args):
    """List Bitcoin addresses and statistics"""
    stats = get_bitcoin_address_stats()

    print("\n📊 Bitcoin Address Statistics")
    print("-" * 40)
    print(f"Total addresses:     {stats['total']}")
    print(f"Available addresses: {stats['available']}")
    print(f"Used addresses:      {stats['used']}")

    if args.show_all:
        with Database().session() as session:
            addresses = session.query(BitcoinAddress).all()

            if addresses:
                print(f"\n{'Address':<45} {'Status':<10} {'Used By':<15}")
                print("-" * 70)

                for addr in addresses:
                    status = "Used" if addr.is_used else "Available"
                    used_by = str(addr.used_by) if addr.used_by else "-"
                    print(f"{addr.address:<45} {status:<10} {used_by:<15}")


def update_inventory(args):
    """Update item inventory using new stock management system"""
    with Database().session() as session:
        # Find the item
        item = session.query(Goods).filter_by(name=args.item_name).first()

        if not item:
            print(f"❌ Item not found: {args.item_name}")
            return

        # Get current stock count
        current_stock = item.stock_quantity

        # Determine action and target stock
        if args.set is not None:
            # Set to specific value
            target_stock = args.set
        elif args.add is not None:
            # Add to current stock
            target_stock = current_stock + args.add
        elif args.remove is not None:
            # Remove from current stock
            target_stock = max(0, current_stock - args.remove)
        else:
            print("❌ Must specify --set, --add, or --remove")
            return

        # Get admin user ID for logging
        admin_id = get_admin_user_id() or 0

        # Perform the inventory update
        if args.set is not None:
            # Set exact stock
            old_stock = item.stock_quantity
            item.stock_quantity = target_stock
            session.commit()

            # Log the change using inventory system
            from bot.database.methods.inventory import log_inventory_change
            log_inventory_change(
                session=session,
                item_name=args.item_name,
                change_type='manual',
                quantity_change=target_stock - old_stock,
                admin_id=admin_id,
                comment=f"CLI: Stock set to {target_stock} (was {old_stock})"
            )

        elif args.add is not None:
            # Add inventory using inventory management system
            success, msg = add_inventory(
                item_name=args.item_name,
                quantity=args.add,
                admin_id=admin_id,
                comment=f"CLI: Added {args.add} units",
                session=session
            )
            if not success:
                print(f"❌ Failed to add inventory: {msg}")
                return
            session.commit()

        elif args.remove is not None:
            # Remove from stock
            if args.remove > item.stock_quantity:
                print(f"❌ Cannot remove {args.remove} units. Only {item.stock_quantity} available.")
                return

            old_stock = item.stock_quantity
            item.stock_quantity -= args.remove
            session.commit()

            # Log the change
            from bot.database.methods.inventory import log_inventory_change
            log_inventory_change(
                session=session,
                item_name=args.item_name,
                change_type='manual',
                quantity_change=-args.remove,
                admin_id=admin_id,
                comment=f"CLI: Removed {args.remove} units"
            )

        # Get final stock
        session.refresh(item)
        final_stock = item.stock_quantity

        # Log inventory update
        log_inventory_update(
            item_name=args.item_name,
            old_stock=current_stock,
            new_stock=final_stock,
            updated_by=admin_id,
            updated_by_username='admin_cli',
            method='CLI'
        )

        log_audit(
            "inventory_updated", user_id=admin_id or None,
            resource_type="Goods", resource_id=args.item_name,
            details=f"stock {current_stock} -> {final_stock} (CLI)",
            session=session,
        )

        print(f"✅ Inventory updated for '{args.item_name}'")
        print(f"   Old stock: {current_stock}")
        print(f"   New stock: {final_stock}")
        print(f"   Reserved: {item.reserved_quantity}")
        print(f"   Available: {final_stock - item.reserved_quantity}")


def export_data(args):
    """Export data for backup"""
    export_dir = Path(args.output_dir)
    export_dir.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print(f"Exporting data to {export_dir}...")

    # Export customer CSV
    if args.customers or args.all:
        asyncio.run(sync_all_customers_to_csv())
        customer_file = export_dir / f"customers_{timestamp}.csv"
        if export_customers_csv(customer_file):
            print(f"✅ Exported customers to {customer_file}")

    # Export reference codes
    if args.refcodes or args.all:
        refcode_file = export_dir / f"reference_codes_{timestamp}.csv"
        with Database().session() as session:
            codes = session.query(ReferenceCode).all()
            import csv
            with open(refcode_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Code', 'Created By', 'Created At', 'Expires At', 'Max Uses', 'Current Uses', 'Active',
                                 'Admin Code', 'Note'])
                for code in codes:
                    writer.writerow([
                        code.code, code.created_by, code.created_at,
                        code.expires_at, code.max_uses, code.current_uses,
                        code.is_active, code.is_admin_code, code.note or ''
                    ])
        print(f"✅ Exported reference codes to {refcode_file}")

    # Export orders
    if args.orders or args.all:
        orders_file = export_dir / f"orders_{timestamp}.csv"
        with Database().session() as session:
            orders = session.query(Order).all()
            import csv
            with open(orders_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['ID', 'Buyer ID', 'Item', 'Price', 'Quantity', 'Payment Method', 'Status', 'Created At',
                     'Completed At',
                     'Phone', 'Address'])
                for order in orders:
                    if order.items:
                        for item in order.items:
                            writer.writerow([
                                order.id, order.buyer_id, item.item_name, item.price, item.quantity,
                                order.payment_method, order.order_status, order.created_at,
                                order.completed_at, order.phone_number, order.delivery_address
                            ])
                    else:
                        writer.writerow([
                            order.id, order.buyer_id, '', '', 0,
                            order.payment_method, order.order_status, order.created_at,
                            order.completed_at, order.phone_number, order.delivery_address
                        ])
        print(f"✅ Exported orders to {orders_file}")

    print("\n✅ Export completed!")


def set_setting(args):
    """Update bot settings"""
    with Database().session() as session:
        setting = session.query(BotSettings).filter_by(setting_key=args.key).first()

        if setting:
            setting.setting_value = args.value
        else:
            setting = BotSettings(setting_key=args.key, setting_value=args.value)
            session.add(setting)

        session.commit()

    print(f"✅ Setting updated: {args.key} = {args.value}")

    # Special handling for timezone - reload for hot reload support
    if args.key == 'timezone':
        tz_config.reload_timezone()
        print(f"⏰ Timezone reloaded: {tz_config.get_timezone()}")


def get_setting(args):
    """Get bot setting value"""
    with Database().session() as session:
        setting = session.query(BotSettings).filter_by(setting_key=args.key).first()

        if setting:
            print(f"{args.key} = {setting.setting_value}")
        else:
            print(f"❌ Setting not found: {args.key}")


def list_settings(args):
    """List all bot settings"""
    with Database().session() as session:
        settings = session.query(BotSettings).order_by(BotSettings.setting_key).all()

        if not settings:
            print("No settings found")
            return

        print(f"\n{'Setting Key':<30} {'Value':<50}")
        print("-" * 80)

        for setting in settings:
            print(f"{setting.setting_key:<30} {setting.setting_value or 'NULL':<50}")


async def ban_user_cli(args):
    """Ban a user via CLI"""
    try:
        user_id = int(args.user_id)
    except ValueError:
        print(f"❌ Invalid user ID: {args.user_id}")
        return

    # Get admin user ID
    admin_id = get_admin_user_id()
    if not admin_id:
        print("❌ Error: No admin user found. Set OWNER_ID environment variable.")
        return

    # Check if user exists
    with Database().session() as session:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            print(f"❌ User not found: {user_id}")
            return

        if user.is_banned:
            print(f"⚠️  User {user_id} is already banned")
            return

    # Ban the user
    reason = args.reason or "Banned via CLI"
    success = ban_user(user_id, banned_by=admin_id, reason=reason)

    if success:
        # Get username
        username = await get_telegram_username(user_id)

        log_audit(
            "user_banned", level="WARNING", user_id=admin_id,
            resource_type="User", resource_id=user_id,
            details=f"reason={reason}",
        )

        print(f"✅ User banned successfully")
        print(f"   User: @{username} (ID: {user_id})")
        print(f"   Reason: {reason}")

        # Try to notify the user
        if args.notify:
            try:
                bot = Bot(
                    token=EnvKeys.TOKEN,
                    default=DefaultBotProperties(parse_mode="HTML")
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"⛔ <b>You have been banned</b>\n\nReason: {reason}"
                    )
                    print(f"📧 Ban notification sent to user")
                finally:
                    await bot.session.close()

            except Exception as e:
                print(f"⚠️  Failed to send ban notification: {e}")
    else:
        print(f"❌ Failed to ban user {user_id}")


async def unban_user_cli(args):
    """Unban a user via CLI"""
    try:
        user_id = int(args.user_id)
    except ValueError:
        print(f"❌ Invalid user ID: {args.user_id}")
        return

    # Check if user exists
    with Database().session() as session:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            print(f"❌ User not found: {user_id}")
            return

        if not user.is_banned:
            print(f"⚠️  User {user_id} is not banned")
            return

    # Unban the user
    success = unban_user(user_id)

    if success:
        # Get username
        username = await get_telegram_username(user_id)

        log_audit(
            "user_unbanned", user_id=get_admin_user_id(),
            resource_type="User", resource_id=user_id,
        )

        print(f"✅ User unbanned successfully")
        print(f"   User: @{username} (ID: {user_id})")

        # Try to notify the user
        if args.notify:
            try:
                bot = Bot(
                    token=EnvKeys.TOKEN,
                    default=DefaultBotProperties(parse_mode="HTML")
                )

                try:
                    await bot.send_message(
                        user_id,
                        "✅ <b>You have been unbanned</b>\n\nYou can now use the bot again."
                    )
                    print(f"📧 Unban notification sent to user")
                finally:
                    await bot.session.close()

            except Exception as e:
                print(f"⚠️  Failed to send unban notification: {e}")
    else:
        print(f"❌ Failed to unban user {user_id}")


def manage_sale(args):
    """Set or remove a time-limited sale on a product."""
    from bot.database.methods.update import set_item_sale
    from bot.utils.money import format_sale_percent

    admin_id = get_admin_user_id()

    if args.remove:
        success, error = set_item_sale(args.item_name, None, None)
        if success:
            log_audit("item_sale_removed", user_id=admin_id,
                      resource_type="Goods", resource_id=args.item_name)
            print(f"✅ Sale removed from '{args.item_name}'")
        else:
            print(f"❌ {error}")
        return

    if args.percent is None or args.days is None:
        print("❌ --percent and --days are required (or use --remove)")
        return

    percent = Decimal(str(args.percent))
    if percent <= 0 or percent >= 100:
        print("❌ Percent must be between 1 and 99")
        return
    if args.days <= 0:
        print("❌ Days must be greater than 0")
        return

    until = datetime.now(timezone.utc) + timedelta(days=args.days)
    success, error = set_item_sale(args.item_name, percent, until)
    if success:
        log_audit("item_sale_set", user_id=admin_id,
                  resource_type="Goods", resource_id=args.item_name,
                  details=f"percent={format_sale_percent(percent)}; days={args.days}")
        print(f"✅ Sale -{format_sale_percent(percent)}% set for '{args.item_name}' for {args.days} day(s)")
    else:
        print(f"❌ {error}")


def handle_stats(args):
    """Print shop statistics (parity with the admin 'Statistics' screen and web dashboard)."""
    import datetime as _dt
    from sqlalchemy import func as _func
    from bot.database.methods.read import (
        select_today_users, get_user_count, select_admins,
        select_count_goods, select_count_categories,
    )
    from bot.database.models.main import Order

    today = _dt.date.today().isoformat()
    with Database().session() as s:
        status_rows = s.query(Order.order_status, _func.count(Order.id)).group_by(Order.order_status).all()
        status_counts = {st: c for st, c in status_rows}
        revenue = s.query(_func.coalesce(_func.sum(Order.total_price), 0)).filter(
            Order.order_status.in_(['delivered', 'completed'])
        ).scalar()

    print("=== Shop statistics ===")
    print(f"Users: {get_user_count()}  (admins: {select_admins()}, new today: {select_today_users(today)})")
    print(f"Products: {select_count_goods()}  |  Categories: {select_count_categories()}")
    print("Orders by status:")
    if status_counts:
        for st, c in sorted(status_counts.items()):
            print(f"  • {st}: {c}")
    else:
        print("  (no orders yet)")
    print(f"Revenue (delivered): {revenue} {EnvKeys.PAY_CURRENCY}")


def handle_category(args):
    """Create / list / delete categories."""
    from bot.database.methods import create_category, delete_category
    from bot.database.models.main import Categories
    admin_id = get_admin_user_id()
    sub = args.category_command

    if sub == 'add':
        create_category(args.name)
        log_audit("category_created", user_id=admin_id, resource_type="Category", resource_id=args.name)
        print(f"✅ Category '{args.name}' created")
    elif sub == 'list':
        with Database().session() as s:
            cats = s.query(Categories).all()
            if not cats:
                print("No categories.")
                return
            for c in cats:
                print(f"- {c.name}")
    elif sub == 'delete':
        delete_category(args.name)
        log_audit("category_deleted", level="WARNING", user_id=admin_id, resource_type="Category", resource_id=args.name)
        print(f"✅ Category '{args.name}' deleted")
    else:
        print("Use: category {add|list|delete}")


def handle_item(args):
    """Create / list / delete products (positions)."""
    from bot.database.methods import create_item, delete_item
    from bot.database.methods.inventory import add_inventory
    from bot.database.models.main import Goods
    admin_id = get_admin_user_id()
    sub = args.item_command

    if sub == 'add':
        create_item(args.name, args.description, Decimal(str(args.price)), args.category)
        if args.stock and args.stock > 0:
            add_inventory(item_name=args.name, quantity=args.stock,
                          admin_id=admin_id or 0, comment="CLI: initial stock")
        log_audit("item_created", user_id=admin_id, resource_type="Goods", resource_id=args.name,
                  details=f"price={args.price}; category={args.category}; stock={args.stock or 0}")
        print(f"✅ Item '{args.name}' created")
    elif sub == 'list':
        with Database().session() as s:
            goods = s.query(Goods).all()
            if not goods:
                print("No products.")
                return
            print(f"{'Name':<28} {'Price':<10} {'Category':<18} {'Stock':<7} {'Reserved'}")
            print("-" * 75)
            for g in goods:
                print(f"{g.name:<28} {str(g.price):<10} {g.category_name:<18} {g.stock_quantity:<7} {g.reserved_quantity}")
    elif sub == 'delete':
        delete_item(args.name)
        log_audit("item_deleted", level="WARNING", user_id=admin_id, resource_type="Goods", resource_id=args.name)
        print(f"✅ Item '{args.name}' deleted")
    else:
        print("Use: item {add|list|delete}")


async def broadcast_cli(args):
    """Send a message to all non-banned users."""
    from bot.communication.broadcast_system import BroadcastManager
    from bot.database.models.main import User

    with Database().session() as s:
        user_ids = [u.telegram_id for u in s.query(User).filter(User.is_banned.is_(False)).all()]
    if not user_ids:
        print("No users to broadcast to.")
        return

    bot = Bot(token=EnvKeys.TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        manager = BroadcastManager(bot)
        stats = await manager.broadcast(user_ids, args.message)
        log_audit("broadcast_sent", user_id=get_admin_user_id(),
                  details=f"total={stats.total}; sent={stats.sent}; failed={stats.failed}")
        print(f"✅ Broadcast complete: sent={stats.sent}, failed={stats.failed}, "
              f"blocked={stats.blocked}, total={stats.total}")
    finally:
        await bot.session.close()


def handle_broadcast(args):
    asyncio.run(broadcast_cli(args))


def handle_bonus(args):
    """Grant referral bonus balance to a user (admin-granted, no real order)."""
    from bot.database.models.main import ReferralEarnings
    from bot.export.customer_csv import update_customer_bonus

    try:
        user_id = int(args.user_id)
    except ValueError:
        print(f"❌ Invalid user ID: {args.user_id}")
        return
    amount = Decimal(str(args.amount))
    if amount <= 0:
        print("❌ Amount must be positive")
        return

    admin_id = get_admin_user_id()
    with Database().session() as session:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            print(f"❌ User not found: {user_id}")
            return
        session.add(ReferralEarnings(
            referrer_id=user_id, referral_id=None,
            amount=amount, original_amount=Decimal('0'),
            created_at=datetime.now(timezone.utc),
        ))

    username = get_username_by_telegram_id(user_id) or f"user_{user_id}"
    update_customer_bonus(user_id, username, amount)
    log_audit("admin_bonus_granted", user_id=admin_id, resource_type="User",
              resource_id=user_id, details=f"amount={amount}")
    print(f"✅ Granted {format_price(amount)} bonus to user {user_id}")


def promo_cli(args):
    """Manage promo codes from the CLI."""
    from bot.database.methods.promo import (
        create_promo_code, list_promo_codes, set_promo_active, delete_promo_code,
    )
    from bot.utils.money import format_sale_percent, format_price, as_datetime

    admin_id = get_admin_user_id()
    sub = args.promo_command

    if sub == 'create':
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=args.expires_hours)) if args.expires_hours > 0 else None
        ok, reason = create_promo_code(
            code=args.code, discount_type=args.type, discount_value=Decimal(str(args.value)),
            category_name=args.category, item_name=args.item,
            max_uses=(args.max_uses or None), expires_at=expires_at, created_by=admin_id,
        )
        if ok:
            log_audit("promo_created", user_id=admin_id, resource_type="PromoCode",
                      resource_id=args.code.upper(), details=f"{args.type}={args.value}")
            print(f"✅ Promo code {args.code.upper()} created")
        else:
            print(f"❌ Failed to create promo code: {reason}")

    elif sub == 'list':
        promos = list_promo_codes(active_only=args.active_only, limit=100)
        if not promos:
            print("No promo codes found.")
            return
        print(f"{'Code':<20} {'Type':<8} {'Value':<10} {'Uses':<10} {'Active':<7} Expires")
        print("-" * 80)
        for p in promos:
            value = f"{format_sale_percent(p['discount_value'])}%" if p['discount_type'] == 'percent' else format_price(p['discount_value'])
            uses = f"{p['current_uses']}/{p['max_uses'] if p['max_uses'] is not None else '∞'}"
            exp = as_datetime(p['expires_at'])
            exp_str = exp.strftime('%Y-%m-%d %H:%M') if exp else 'never'
            print(f"{p['code']:<20} {p['discount_type']:<8} {value:<10} {uses:<10} {str(p['is_active']):<7} {exp_str}")

    elif sub in ('enable', 'disable'):
        active = sub == 'enable'
        if set_promo_active(args.code, active):
            log_audit("promo_toggled", user_id=admin_id, resource_type="PromoCode",
                      resource_id=args.code.upper(), details=f"active={active}")
            print(f"✅ Promo code {args.code.upper()} {'enabled' if active else 'disabled'}")
        else:
            print(f"❌ Promo code {args.code.upper()} not found")

    elif sub == 'delete':
        if delete_promo_code(args.code):
            log_audit("promo_deleted", level="WARNING", user_id=admin_id,
                      resource_type="PromoCode", resource_id=args.code.upper())
            print(f"✅ Promo code {args.code.upper()} deleted")
        else:
            print(f"❌ Promo code {args.code.upper()} not found")
    else:
        print("Use: promo {create|list|enable|disable|delete}")


def main():
    parser = argparse.ArgumentParser(
        description='Telegram Shop Bot CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Order management
    order_parser = subparsers.add_parser('order', help='Manage orders')
    order_parser.add_argument('--order-code', required=True, help='Order code (e.g., ECBDJI)')

    order_action = order_parser.add_mutually_exclusive_group(required=True)
    order_action.add_argument('--complete', action='store_true',
                              help='[DEPRECATED] Mark order as completed (use --status-delivered)')
    order_action.add_argument('--cancel', action='store_true', help='Cancel order')
    order_action.add_argument('--status-confirmed', action='store_true', help='Confirm order with delivery time')
    order_action.add_argument('--status-delivered', action='store_true',
                              help='Mark order as delivered (deducts inventory)')
    order_action.add_argument('--add-item', metavar='ITEM_NAME', help='Add item to order')
    order_action.add_argument('--remove-item', metavar='ITEM_NAME', help='Remove item from order')
    order_action.add_argument('--update-delivery-time', action='store_true', help='Update delivery time')

    # Additional arguments for specific actions
    order_parser.add_argument('--delivery-time', help='Delivery time in format "YYYY-MM-DD HH:MM"')
    order_parser.add_argument('--quantity', type=int, default=1, help='Quantity for add/remove item (default: 1)')
    order_parser.add_argument('--notify', action='store_true', help='Notify customer about changes')

    def handle_order_action(args):
        """Handle order actions based on flags"""
        if args.complete:
            # Deprecated: redirect to new flow
            print("⚠️  --complete is deprecated. Use --status-delivered instead.")
            asyncio.run(complete_order_by_code(args.order_code))
        elif args.cancel:
            asyncio.run(cancel_order_by_code(args.order_code))
        elif args.status_confirmed:
            if not args.delivery_time:
                print("❌ --delivery-time is required with --status-confirmed")
                print("   Example: --delivery-time \"2025-11-16 18:45\"")
                return
            asyncio.run(confirm_order_with_delivery_time(args.order_code, args.delivery_time))
        elif args.status_delivered:
            asyncio.run(mark_order_delivered(args.order_code))
        elif args.add_item:
            asyncio.run(add_item_to_order(args.order_code, args.add_item, args.quantity, args.notify))
        elif args.remove_item:
            asyncio.run(remove_item_from_order(args.order_code, args.remove_item, args.quantity, args.notify))
        elif args.update_delivery_time:
            if not args.delivery_time:
                print("❌ --delivery-time is required with --update-delivery-time")
                print("   Example: --delivery-time \"2025-11-16 20:00\"")
                return
            asyncio.run(update_delivery_time(args.order_code, args.delivery_time, args.notify))

    order_parser.set_defaults(func=handle_order_action)

    # Reference code management
    refcode_parser = subparsers.add_parser('refcode', help='Manage reference codes')
    refcode_sub = refcode_parser.add_subparsers(dest='refcode_command')

    # Create reference code
    create_ref = refcode_sub.add_parser('create', help='Create a reference code')
    create_ref.add_argument('--created-by', type=int, help='User ID creating the code (defaults to first admin)')
    create_ref.add_argument('--expires-hours', type=int, default=0, help='Expiration in hours (0 for never)')
    create_ref.add_argument('--max-uses', type=int, default=0, help='Maximum uses (0 for unlimited)')
    create_ref.add_argument('--note', type=str, help='Optional note')
    create_ref.set_defaults(func=create_refcode)

    # Disable reference code
    disable_ref = refcode_sub.add_parser('disable', help='Disable a reference code')
    disable_ref.add_argument('code', help='Reference code to disable')
    disable_ref.add_argument('--reason', help='Reason for disabling')
    disable_ref.set_defaults(func=disable_refcode)

    # List reference codes
    list_ref = refcode_sub.add_parser('list', help='List reference codes')
    list_ref.add_argument('--active-only', action='store_true', help='Show only active codes')
    list_ref.set_defaults(func=list_refcodes)

    # Bitcoin address management
    btc_parser = subparsers.add_parser('btc', help='Manage Bitcoin addresses')
    btc_sub = btc_parser.add_subparsers(dest='btc_command')

    # Add Bitcoin address
    add_btc = btc_sub.add_parser('add', help='Add Bitcoin address(es)')
    add_btc.add_argument('--address', help='Single Bitcoin address')
    add_btc.add_argument('--file', help='File with Bitcoin addresses (one per line)')
    add_btc.set_defaults(func=add_btc_address)

    # List Bitcoin addresses
    list_btc = btc_sub.add_parser('list', help='List Bitcoin addresses')
    list_btc.add_argument('--show-all', action='store_true', help='Show all addresses')
    list_btc.set_defaults(func=list_btc_addresses)

    # Update inventory
    inv_parser = subparsers.add_parser('inventory', help='Update item inventory')
    inv_parser.add_argument('item_name', help='Item name')
    inv_group = inv_parser.add_mutually_exclusive_group(required=True)
    inv_group.add_argument('--set', type=int, help='Set inventory to specific value')
    inv_group.add_argument('--add', type=int, help='Add to current inventory')
    inv_group.add_argument('--remove', type=int, help='Remove from current inventory')
    inv_parser.set_defaults(func=update_inventory)

    # Export data
    export_parser = subparsers.add_parser('export', help='Export data for backup')
    export_parser.add_argument('--output-dir', default='backups', help='Output directory')
    export_parser.add_argument('--all', action='store_true', help='Export all data')
    export_parser.add_argument('--customers', action='store_true', help='Export customers')
    export_parser.add_argument('--refcodes', action='store_true', help='Export reference codes')
    export_parser.add_argument('--orders', action='store_true', help='Export orders')
    export_parser.set_defaults(func=export_data)

    # Settings management
    settings_parser = subparsers.add_parser('settings', help='Manage bot settings')
    settings_sub = settings_parser.add_subparsers(dest='settings_command')

    # Set setting
    set_parser = settings_sub.add_parser('set', help='Set a setting value')
    set_parser.add_argument('key', help='Setting key')
    set_parser.add_argument('value', help='Setting value')
    set_parser.set_defaults(func=set_setting)

    # Get setting
    get_parser = settings_sub.add_parser('get', help='Get a setting value')
    get_parser.add_argument('key', help='Setting key')
    get_parser.set_defaults(func=get_setting)

    # List settings
    list_set_parser = settings_sub.add_parser('list', help='List all settings')
    list_set_parser.set_defaults(func=list_settings)

    # User ban management
    ban_parser = subparsers.add_parser('ban', help='Ban a user')
    ban_parser.add_argument('user_id', help='Telegram ID of user to ban')
    ban_parser.add_argument('--reason', help='Reason for ban', default=None)
    ban_parser.add_argument('--notify', action='store_true', help='Notify user about ban')

    def handle_ban(args):
        asyncio.run(ban_user_cli(args))

    ban_parser.set_defaults(func=handle_ban)

    # User unban management
    unban_parser = subparsers.add_parser('unban', help='Unban a user')
    unban_parser.add_argument('user_id', help='Telegram ID of user to unban')
    unban_parser.add_argument('--notify', action='store_true', help='Notify user about unban')

    def handle_unban(args):
        asyncio.run(unban_user_cli(args))

    unban_parser.set_defaults(func=handle_unban)

    # Shop statistics
    stats_parser = subparsers.add_parser('stats', help='Show shop statistics')
    stats_parser.set_defaults(func=handle_stats)

    # Grant referral bonus
    bonus_parser = subparsers.add_parser('bonus', help='Grant referral bonus to a user')
    bonus_parser.add_argument('user_id', help='Telegram ID of the user')
    bonus_parser.add_argument('amount', help='Bonus amount to grant')
    bonus_parser.set_defaults(func=handle_bonus)

    # Category management
    category_parser = subparsers.add_parser('category', help='Manage categories')
    category_sub = category_parser.add_subparsers(dest='category_command')
    cat_add = category_sub.add_parser('add', help='Create a category')
    cat_add.add_argument('name', help='Category name')
    cat_add.set_defaults(func=handle_category)
    cat_list = category_sub.add_parser('list', help='List categories')
    cat_list.set_defaults(func=handle_category)
    cat_del = category_sub.add_parser('delete', help='Delete a category (and its products)')
    cat_del.add_argument('name', help='Category name')
    cat_del.set_defaults(func=handle_category)

    # Product (item) management
    item_parser = subparsers.add_parser('item', help='Manage products')
    item_sub = item_parser.add_subparsers(dest='item_command')
    item_add = item_sub.add_parser('add', help='Create a product')
    item_add.add_argument('name', help='Product name')
    item_add.add_argument('--description', required=True, help='Product description')
    item_add.add_argument('--price', type=float, required=True, help='Price')
    item_add.add_argument('--category', required=True, help='Category name (must exist)')
    item_add.add_argument('--stock', type=int, default=0, help='Initial stock quantity')
    item_add.set_defaults(func=handle_item)
    item_list = item_sub.add_parser('list', help='List products')
    item_list.set_defaults(func=handle_item)
    item_del = item_sub.add_parser('delete', help='Delete a product')
    item_del.add_argument('name', help='Product name')
    item_del.set_defaults(func=handle_item)

    # Broadcast
    broadcast_parser = subparsers.add_parser('broadcast', help='Send a message to all users')
    broadcast_parser.add_argument('message', help='Message text (HTML allowed)')
    broadcast_parser.set_defaults(func=handle_broadcast)

    # Promo code management
    promo_parser = subparsers.add_parser('promo', help='Manage promo codes')
    promo_sub = promo_parser.add_subparsers(dest='promo_command')
    p_create = promo_sub.add_parser('create', help='Create a promo code')
    p_create.add_argument('code', help='Promo code text')
    p_create.add_argument('--type', choices=['percent', 'fixed'], required=True, help='Discount type')
    p_create.add_argument('--value', type=float, required=True, help='Discount value')
    p_create.add_argument('--category', help='Bind to a category (optional)')
    p_create.add_argument('--item', help='Bind to a single item (optional)')
    p_create.add_argument('--max-uses', type=int, default=0, help='Max total uses (0 = unlimited)')
    p_create.add_argument('--expires-hours', type=int, default=0, help='Validity in hours (0 = never)')
    p_create.set_defaults(func=promo_cli)
    p_list = promo_sub.add_parser('list', help='List promo codes')
    p_list.add_argument('--active-only', action='store_true', help='Show only active codes')
    p_list.set_defaults(func=promo_cli)
    p_enable = promo_sub.add_parser('enable', help='Enable a promo code')
    p_enable.add_argument('code')
    p_enable.set_defaults(func=promo_cli)
    p_disable = promo_sub.add_parser('disable', help='Disable a promo code')
    p_disable.add_argument('code')
    p_disable.set_defaults(func=promo_cli)
    p_delete = promo_sub.add_parser('delete', help='Delete a promo code')
    p_delete.add_argument('code')
    p_delete.set_defaults(func=promo_cli)

    # Time-limited sale management
    sale_parser = subparsers.add_parser('sale', help='Manage a product time-limited sale')
    sale_parser.add_argument('item_name', help='Product name')
    sale_parser.add_argument('--percent', type=float, help='Discount percent (1-99)')
    sale_parser.add_argument('--days', type=int, help='Duration in days')
    sale_parser.add_argument('--remove', action='store_true', help='Remove the active sale')
    sale_parser.set_defaults(func=manage_sale)

    # Audit log query
    audit_parser = subparsers.add_parser('audit', help='View the audit log')
    audit_parser.add_argument('--limit', type=int, default=50, help='Max entries to show (default 50)')
    audit_parser.add_argument('--action', help='Filter by action name (e.g. order_delivered)')
    audit_parser.add_argument('--user', type=int, help='Filter by actor user id')

    def handle_audit(args):
        rows = get_recent_audit_logs(limit=args.limit, action=args.action, user_id=args.user)
        if not rows:
            print("No audit entries found.")
            return
        print(f"{'Time (UTC)':<20} {'Level':<8} {'Action':<20} {'User':<12} {'Resource':<24} Details")
        print("-" * 110)
        for r in rows:
            ts = r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r['created_at'] else '-'
            resource = f"{r['resource_type'] or ''}:{r['resource_id'] or ''}".strip(':')
            print(f"{ts:<20} {r['level']:<8} {r['action']:<20} {str(r['user_id'] or '-'):<12} "
                  f"{resource:<24} {r['details'] or ''}")

    audit_parser.set_defaults(func=handle_audit)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
