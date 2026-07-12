from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from bot.database.models.main import Order
from bot.i18n import localize
from bot.config.env import EnvKeys
from bot.utils.money import format_price


async def send_order_notification(telegram_id: int, message_text: str) -> bool:
    """
    Send a notification message to user via Telegram

    Args:
        telegram_id: Telegram user ID
        message_text: Message to send

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        bot = Bot(
            token=EnvKeys.TOKEN,
            default=DefaultBotProperties(parse_mode="HTML")
        )

        try:
            await bot.send_message(telegram_id, message_text)
            return True
        finally:
            await bot.session.close()

    except Exception as e:
        # Avoid emoji in print for Windows console compatibility
        print(f"[WARNING] Failed to send notification to {telegram_id}: {str(e)[:100]}")
        return False


def format_order_items(items: list) -> str:
    """
    Format order items for display

    Args:
        items: List of OrderItem objects

    Returns:
        Formatted string with items list
    """
    if not items:
        return "N/A"

    items_list = [f"  • {item.item_name} x {item.quantity} - {format_price(item.price * item.quantity)}"
                  for item in items]
    return "\n".join(items_list)


async def notify_order_confirmed(order: Order, items: list, delivery_time: datetime) -> bool:
    """
    Send order confirmation notification to customer

    Args:
        order: Order object
        items: List of OrderItem objects
        delivery_time: Planned delivery time

    Returns:
        True if sent successfully
    """

    # Format delivery time
    delivery_time_str = delivery_time.strftime("%Y-%m-%d %H:%M")

    # Format items
    items_formatted = format_order_items(items)

    # Format message
    message = localize("order.status.notify_order_confirmed",
                       order_code=order.order_code,
                       delivery_time=delivery_time_str,
                       items=items_formatted,
                       total=f"{order.total_price} {EnvKeys.PAY_CURRENCY}"
                       )

    return await send_order_notification(order.buyer_id, message)


async def notify_order_delivered(order: Order) -> bool:
    """
    Send order delivery confirmation to customer

    Args:
        order: Order object

    Returns:
        True if sent successfully
    """
    # Format message
    message = localize("order.status.notify_order_delivered",
                       order_code=order.order_code,
                       total=format_price(order.total_price)
                       )

    return await send_order_notification(order.buyer_id, message)


async def notify_order_modified(order: Order, changes_description: str) -> bool:
    """
    Send order modification notification to customer

    Args:
        order: Order object
        changes_description: Description of changes made

    Returns:
        True if sent successfully
    """
    # Format message
    message = localize("order.status.notify_order_modified",
                       order_code=order.order_code,
                       changes=changes_description,
                       total=format_price(order.total_price)
                       )

    return await send_order_notification(order.buyer_id, message)
