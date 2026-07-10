import asyncio
import datetime
from decimal import Decimal
from functools import wraps
from typing import Optional, Dict

from sqlalchemy import func

from bot.database.models import Database, User, Goods, Categories, Role, BoughtGoods, \
    Operations, ReferralEarnings, BotSettings, ShoppingCart, OrderItem, Order
from bot.caching import get_cache_manager


async def run_db(func, *args, **kwargs):
    """Run a synchronous DB callable in the default thread-pool executor.

    Lets async handlers/middleware call the sync data layer without blocking the
    event loop. Use this on hot paths (checkout writes, middleware role checks).
    """
    loop = asyncio.get_running_loop()
    if kwargs:
        from functools import partial
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))
    return await loop.run_in_executor(None, func, *args)


# Wrapper for synchronous functions to asynchronous functions with caching
def async_cached(ttl: int = 300, key_prefix: str = ""):
    def decorator(sync_func):
        @wraps(sync_func)
        async def async_wrapper(*args, **kwargs):
            # Generate the cache key
            cache_key = f"{key_prefix or sync_func.__name__}:{':'.join(str(arg) for arg in args)}"

            cache = get_cache_manager()
            if cache:
                # Trying to get it from the cache
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

            # Execute synchronous function in executor
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, sync_func, *args)

            # Save to cache
            if cache and result is not None:
                await cache.set(cache_key, result, ttl)

            return result

        return async_wrapper

    return decorator


def _day_window(date_str: str) -> tuple[datetime.datetime, datetime.datetime]:
    d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    start = datetime.datetime.combine(d, datetime.time.min)
    end = start + datetime.timedelta(days=1)
    return start, end


def check_user(telegram_id: int | str) -> Optional[User]:
    """Return user by Telegram ID or None if not found."""
    with Database().session() as s:
        result = s.query(User).filter(User.telegram_id == telegram_id).one_or_none()
        return result.__dict__ if result else None


def check_role(telegram_id: int) -> int:
    """Return permission bitmask for user (0 if none)."""
    with Database().session() as s:
        role_id = s.query(User.role_id).filter(User.telegram_id == telegram_id).scalar()
        if not role_id:
            return 0
        perms = s.query(Role.permissions).filter(Role.id == role_id).scalar()
        return perms or 0


def get_role_id_by_name(role_name: str) -> Optional[int]:
    """Return role id by name or None."""
    with Database().session() as s:
        return s.query(Role.id).filter(Role.name == role_name).scalar()


def check_role_name_by_id(role_id: int) -> str:
    """Return role name by id (raises if not found)."""
    with Database().session() as s:
        return s.query(Role.name).filter(Role.id == role_id).one()[0]


def select_max_role_id() -> Optional[int]:
    """Return max role id (or None if no roles)."""
    with Database().session() as s:
        return s.query(func.max(Role.id)).scalar()


def select_today_users(date: str) -> int:
    """Return count of users registered on given date (YYYY-MM-DD)."""
    start_of_day, end_of_day = _day_window(date)
    with Database().session() as s:
        return s.query(User).filter(
            User.registration_date >= start_of_day,
            User.registration_date < end_of_day
        ).count()


def get_user_count() -> int:
    """Return total users count."""
    with Database().session() as s:
        return s.query(User).count()


def select_admins() -> int:
    """Return count of users with role_id > 1."""
    with Database().session() as s:
        return s.query(func.count(User.telegram_id)).filter(User.role_id > 1).scalar() or 0


def get_all_users() -> list[tuple[int]]:
    """Return list of all user telegram_ids (as tuples)."""
    with Database().session() as s:
        return s.query(User.telegram_id).all()


def get_bought_item_info(item_id: str) -> dict | None:
    """Return bought item row as dict by row id, or None."""
    with Database().session() as s:
        result = s.query(BoughtGoods).filter(BoughtGoods.id == item_id).first()
        return result.__dict__ if result else None


def get_item_info(item_name: str) -> dict | None:
    """Return item (position) row as dict by name, or None."""
    with Database().session() as s:
        result = s.query(Goods).filter(Goods.name == item_name).first()
        return result.__dict__ if result else None


def get_goods_info(item_name: str) -> dict | None:
    """Return goods row as dict by name, or None. (Replaced ItemValues with Goods)"""
    with Database().session() as s:
        result = s.query(Goods).filter(Goods.name == item_name).first()
        return result.__dict__ if result else None


def check_item(item_name: str) -> dict | None:
    """Return item (position) as dict by name, or None."""
    with Database().session() as s:
        result = s.query(Goods).filter(Goods.name == item_name).first()
        return result.__dict__ if result else None


def check_category(category_name: str) -> dict | None:
    """Return category as dict by name, or None."""
    with Database().session() as s:
        result = s.query(Categories).filter(Categories.name == category_name).first()
        return result.__dict__ if result else None


def select_item_values_amount(item_name: str) -> int:
    """Return available stock for an item (stock_quantity - reserved_quantity)."""
    with Database().session() as s:
        goods = s.query(Goods).filter(Goods.name == item_name).first()
        if not goods:
            return 0
        return goods.available_quantity


def check_value(item_name: str) -> bool:
    """For physical goods, always returns False (no infinite items). Kept for backward compatibility."""
    return False


def select_user_items(buyer_id: int | str) -> int:
    """Return count of bought items for user."""
    with Database().session() as s:
        return s.query(func.count()).filter(BoughtGoods.buyer_id == buyer_id).scalar() or 0


def select_bought_item(unique_id: int) -> dict | None:
    """Return one bought item by unique_id as dict, or None."""
    with Database().session() as s:
        result = s.query(BoughtGoods).filter(BoughtGoods.unique_id == unique_id).first()
        return result.__dict__ if result else None


def select_count_items() -> int:
    """Return total stock quantity across all goods."""
    with Database().session() as s:
        result = s.query(func.sum(Goods.stock_quantity)).scalar()
        return int(result) if result else 0


def select_count_goods() -> int:
    """Return total count of goods (positions)."""
    with Database().session() as s:
        return s.query(Goods).count()


def select_count_categories() -> int:
    """Return total count of categories."""
    with Database().session() as s:
        return s.query(Categories).count()


def select_count_bought_items() -> int:
    """Return total count of bought items."""
    with Database().session() as s:
        return s.query(BoughtGoods).count()


def select_today_orders(date: str) -> Decimal:
    """Return total revenue for given date (YYYY-MM-DD)."""
    start_of_day, end_of_day = _day_window(date)
    with Database().session() as s:
        res = (
            s.query(func.sum(BoughtGoods.price))
            .filter(
                BoughtGoods.bought_datetime >= start_of_day,
                BoughtGoods.bought_datetime < end_of_day
            )
            .scalar()
        )
        return res or Decimal(0)


def select_all_orders() -> Decimal:
    """Return total revenue for all time (sum of BoughtGoods.price)."""
    with Database().session() as s:
        return s.query(func.sum(BoughtGoods.price)).scalar() or Decimal(0)


def select_today_operations(date: str) -> Decimal:
    """Return total operations value for given date (YYYY-MM-DD)."""
    start_of_day, end_of_day = _day_window(date)
    with Database().session() as s:
        res = (
            s.query(func.sum(Operations.operation_value))
            .filter(
                Operations.operation_time >= start_of_day,
                Operations.operation_time < end_of_day
            )
            .scalar()
        )
        return res or Decimal(0)


def select_all_operations() -> Decimal:
    """Return total operations value for all time."""
    with Database().session() as s:
        return s.query(func.sum(Operations.operation_value)).scalar() or Decimal(0)


def select_user_operations(user_id: int | str) -> list[float]:
    """Return list of operation amounts for user."""
    with Database().session() as s:
        return [row[0] for row in s.query(Operations.operation_value).filter(Operations.user_id == user_id).all()]


def check_user_referrals(user_id: int) -> int:
    """Return count of referrals of the user."""
    with Database().session() as s:
        return s.query(User).filter(User.referral_id == user_id).count()


def get_user_referral(user_id: int) -> Optional[int]:
    """Return referral_id of the user or None."""
    with Database().session() as s:
        result = s.query(User.referral_id).filter(User.telegram_id == user_id).first()
        return result[0] if result else None


def get_referral_earnings_stats(referrer_id: int) -> Dict:
    """
    Get statistics on user referral charges.
    """
    with Database().session() as s:
        stats = s.query(
            func.count(ReferralEarnings.id).label('total_earnings_count'),
            func.sum(ReferralEarnings.amount).label('total_amount'),
            func.sum(ReferralEarnings.original_amount).label('total_original_amount'),
            func.count(func.distinct(ReferralEarnings.referral_id)).label('active_referrals_count')
        ).filter(
            ReferralEarnings.referrer_id == referrer_id
        ).first()

        return {
            'total_earnings_count': stats.total_earnings_count or 0,
            'total_amount': stats.total_amount or Decimal(0),
            'total_original_amount': stats.total_original_amount or Decimal(0),
            'active_referrals_count': stats.active_referrals_count or 0
        }


def get_one_referral_earning(earning_id: int) -> dict | None:
    """
    Get one user referral earning info.
    """
    with Database().session() as s:
        result = s.query(ReferralEarnings).filter(ReferralEarnings.id == earning_id).first()
        return result.__dict__ if result else None


def get_reference_bonus_percent() -> Decimal:
    """
    Get reference_bonus_percent from bot_settings.
    Returns Decimal value (default 0).
    """
    with Database().session() as s:
        setting = s.query(BotSettings).filter(BotSettings.setting_key == 'reference_bonus_percent').first()
        if setting and setting.setting_value:
            try:
                return Decimal(str(setting.setting_value))
            except (ValueError, TypeError):
                return Decimal(0)
        return Decimal(0)


def get_bot_setting(setting_key: str, default: str = None, value_type: type = str) -> any:
    """
    Get a setting value from BotSettings.

    Args:
        setting_key: The setting key to retrieve
        default: Default value if setting not found or invalid
        value_type: Type to convert the value to (str, int, float, Decimal)

    Returns:
        Setting value converted to specified type, or default value
    """
    with Database().session() as s:
        setting = s.query(BotSettings).filter(BotSettings.setting_key == setting_key).first()
        if setting and setting.setting_value:
            try:
                if value_type == int:
                    return int(setting.setting_value)
                elif value_type == float:
                    return float(setting.setting_value)
                elif value_type == Decimal:
                    return Decimal(str(setting.setting_value))
                else:
                    return str(setting.setting_value)
            except (ValueError, TypeError):
                pass  # Fall through to return default

        # Convert default to the requested type if needed
        if default is not None:
            try:
                if value_type == int and not isinstance(default, int):
                    return int(default)
                elif value_type == float and not isinstance(default, float):
                    return float(default)
                elif value_type == Decimal and not isinstance(default, Decimal):
                    return Decimal(str(default))
            except (ValueError, TypeError):
                pass

        return default


async def get_cart_items(user_id: int) -> list:
    """
    Get all items in user's cart with product details

    Args:
        user_id: User's telegram ID

    Returns:
        List of cart items with product info
    """
    with Database().session() as session:
        cart_items = session.query(ShoppingCart, Goods).join(
            Goods, ShoppingCart.item_name == Goods.name
        ).filter(
            ShoppingCart.user_id == user_id
        ).all()

        result = []
        for cart_item, good in cart_items:
            result.append({
                'cart_id': cart_item.id,
                'item_name': cart_item.item_name,
                'quantity': cart_item.quantity,
                'price': good.price,
                'total': Decimal(str(good.price)) * cart_item.quantity
            })
        return result


async def query_user_orders(user_id: int, status: str = None, limit: int = 10, offset: int = 0):
    """
    Query user's orders with optional status filter

    Args:
        user_id: User's telegram ID
        status: Order status filter (pending, completed, cancelled) or None for all
        limit: Number of orders to return
        offset: Offset for pagination

    Returns:
        List of Order objects with items
    """
    with Database().session() as session:
        query = session.query(Order).filter(Order.buyer_id == user_id)

        if status:
            query = query.filter(Order.order_status == status)

        query = query.order_by(Order.created_at.desc())

        orders = query.limit(limit).offset(offset).all()

        # Return order data as dicts to avoid session issues
        result = []
        for order in orders:
            # Get order items
            order_items = session.query(OrderItem).filter(OrderItem.order_id == order.id).all()

            items_data = [{
                'item_name': item.item_name,
                'price': float(item.price),
                'quantity': item.quantity
            } for item in order_items]

            result.append({
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

        return result


async def count_user_orders(user_id: int, status: str = None) -> int:
    """
    Count user's orders

    Args:
        user_id: User's telegram ID
        status: Order status filter or None for all

    Returns:
        Number of orders
    """
    with Database().session() as session:
        query = session.query(Order).filter(Order.buyer_id == user_id)

        if status:
            query = query.filter(Order.order_status == status)

        return query.count()


async def calculate_cart_total(user_id: int) -> int:
    """Calculate total price of all items in cart"""
    items = await get_cart_items(user_id)
    return sum(item['total'] for item in items)


@async_cached(ttl=60, key_prefix="user")
def check_user_cached(telegram_id: int | str):
    """Cached version of check_user"""
    return check_user(telegram_id)


@async_cached(ttl=300, key_prefix="role")
def check_role_cached(telegram_id: int):
    """Cached Role Verification"""
    return check_role(telegram_id)


@async_cached(ttl=1800, key_prefix="category")
def check_category_cached(category_name: str):
    """Cached Category Check"""
    return check_category(category_name)


@async_cached(ttl=1800, key_prefix="item")
def check_item_cached(item_name: str):
    """Cached product verification"""
    return check_item(item_name)


@async_cached(ttl=900, key_prefix="item_info")
def get_item_info_cached(item_name: str):
    """Cached product information"""
    return get_item_info(item_name)


@async_cached(ttl=300, key_prefix="item_stock")
def select_item_values_amount_cached(item_name: str):
    """Cached available quantity of goods (stock - reserved)"""
    return select_item_values_amount(item_name)


@async_cached(ttl=60, key_prefix="user_count")
def get_user_count_cached():
    """Cached number of users"""
    return get_user_count()


@async_cached(ttl=60, key_prefix="admin_count")
def select_admins_cached():
    """Cached number of admins"""
    return select_admins()


# Cache invalidation functions
async def invalidate_user_cache(user_id: int):
    """Invalidate user cache"""
    cache = get_cache_manager()
    if cache:
        await cache.delete(f"user:{user_id}")
        await cache.delete(f"role:{user_id}")
        await cache.invalidate_pattern(f"user_stats:{user_id}:*")
        await cache.invalidate_pattern(f"user_items:{user_id}:*")


async def invalidate_item_cache(item_name: str):
    """Invalidate product cache"""
    cache = get_cache_manager()
    if cache:
        await cache.delete(f"item:{item_name}")
        await cache.delete(f"item_info:{item_name}")
        await cache.delete(f"item_stock:{item_name}")  # Updated from item_values
        # Also invalidate categories, as the number of items may have changed
        await cache.invalidate_pattern("category:*")


async def invalidate_category_cache(category_name: str):
    """Invalidate category cache"""
    cache = get_cache_manager()
    if cache:
        await cache.delete(f"category:{category_name}")
        await cache.invalidate_pattern(f"category_items:{category_name}:*")
