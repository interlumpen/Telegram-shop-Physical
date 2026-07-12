from sqlalchemy import exc
from datetime import datetime, timezone

from bot.database.methods import invalidate_user_cache, invalidate_item_cache, invalidate_category_cache
from bot.database.methods.cache_utils import safe_create_task
from bot.database.models import User, Goods, Categories, BoughtGoods
from bot.database import Database
from bot.i18n import localize


def set_role(telegram_id: int, role: int) -> None:
    """Set user's role (by Telegram ID) and commit."""
    with Database().session() as s:
        s.query(User).filter(User.telegram_id == telegram_id).update(
            {User.role_id: role}
        )

    # Invalidate the user cache
    safe_create_task(invalidate_user_cache(telegram_id))


def set_item_sale(item_name: str, sale_percent, sale_until) -> tuple[bool, str | None]:
    """Set or clear a time-limited sale on a product.

    Pass sale_percent=None or sale_until=None to remove the sale.
    """
    try:
        with Database().session() as session:
            goods = session.query(Goods).filter(
                Goods.name == item_name
            ).with_for_update().one_or_none()

            if not goods:
                return False, localize("admin.goods.update.position.invalid")

            if sale_percent is None or sale_until is None:
                goods.sale_percent = None
                goods.sale_until = None
            else:
                goods.sale_percent = sale_percent
                goods.sale_until = sale_until

            safe_create_task(invalidate_item_cache(item_name))
            return True, None

    except exc.SQLAlchemyError as e:
        return False, str(e)


def update_item(item_name: str, new_name: str, description: str, price, category: str) -> tuple[bool, str | None]:
    """
    Update a Goods record with proper locking.
    """
    try:
        with Database().session() as session:
            # Blocking goods for updating
            goods = session.query(Goods).filter(
                Goods.name == item_name
            ).with_for_update().one_or_none()

            if not goods:
                return False, localize("admin.goods.update.position.invalid")

            if new_name == item_name:
                goods.description = description
                goods.price = price
                goods.category_name = category
                return True, None

            # Check that the new name is not already taken
            if session.query(Goods).filter(Goods.name == new_name).first():
                return False, localize("admin.goods.update.position.exists")

            # Create a new product with existing stock quantities
            new_goods = Goods(
                name=new_name,
                price=price,
                description=description,
                category_name=category,
                stock_quantity=goods.stock_quantity,
                reserved_quantity=goods.reserved_quantity
            )
            session.add(new_goods)
            session.flush()

            # Update linked records
            session.query(BoughtGoods).filter(BoughtGoods.item_name == item_name) \
                .update({BoughtGoods.item_name: new_name}, synchronize_session=False)

            # Update inventory log references
            from bot.database.models.main import InventoryLog
            session.query(InventoryLog).filter(InventoryLog.item_name == item_name) \
                .update({InventoryLog.item_name: new_name}, synchronize_session=False)

            # Remove the old merchandise
            session.query(Goods).filter(Goods.name == item_name).delete(synchronize_session=False)

            safe_create_task(invalidate_item_cache(item_name))
            if new_name != item_name:
                safe_create_task(invalidate_item_cache(new_name))

            return True, None

    except exc.SQLAlchemyError as e:
        return False, f"DB Error: {e.__class__.__name__}"


def update_category(category_name: str, new_name: str) -> None:
    """Rename a category with proper transaction handling."""
    with Database().session() as s:
        try:
            s.begin()

            # Block the category
            category = s.query(Categories).filter(
                Categories.name == category_name
            ).with_for_update().one_or_none()

            if not category:
                s.rollback()
                raise ValueError("Category not found")

            # Updating the merchandise
            s.query(Goods).filter(Goods.category_name == category_name).update(
                {Goods.category_name: new_name}
            )

            # Update the category
            category.name = new_name

            s.commit()

            safe_create_task(invalidate_category_cache(category_name))
            if new_name != category_name:
                safe_create_task(invalidate_category_cache(new_name))

        except Exception:
            s.rollback()
            raise


def ban_user(telegram_id: int, banned_by: int, reason: str = None) -> bool:
    """
    Ban a user.

    Args:
        telegram_id: Telegram ID of user to ban
        banned_by: Telegram ID of admin who is banning
        reason: Optional reason for ban

    Returns:
        bool: True if successful, False if user not found or already banned
    """
    with Database().session() as s:
        user = s.query(User).filter(User.telegram_id == telegram_id).with_for_update().one_or_none()

        if not user:
            return False

        if user.is_banned:
            return False  # Already banned

        user.is_banned = True
        user.banned_at = datetime.now(timezone.utc)
        user.banned_by = banned_by
        user.ban_reason = reason

        s.commit()

    # Invalidate the user cache
    safe_create_task(invalidate_user_cache(telegram_id))

    return True


def unban_user(telegram_id: int) -> bool:
    """
    Unban a user.

    Args:
        telegram_id: Telegram ID of user to unban

    Returns:
        bool: True if successful, False if user not found or not banned
    """
    with Database().session() as s:
        user = s.query(User).filter(User.telegram_id == telegram_id).with_for_update().one_or_none()

        if not user:
            return False

        if not user.is_banned:
            return False  # Not banned

        user.is_banned = False
        user.banned_at = None
        user.banned_by = None
        user.ban_reason = None

        s.commit()

    # Invalidate the user cache
    safe_create_task(invalidate_user_cache(telegram_id))

    return True
