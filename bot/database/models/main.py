import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Column, Integer, String, BigInteger, ForeignKey, Text, Boolean,
    DateTime, Numeric, Index, UniqueConstraint, func, JSON
)
from bot.database.main import Database
from sqlalchemy.orm import relationship


class Permission:
    USE = 1
    BROADCAST = 2
    SETTINGS_MANAGE = 4
    USERS_MANAGE = 8
    SHOP_MANAGE = 16
    ADMINS_MANAGE = 32
    OWN = 64


class Role(Database.BASE):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    default = Column(Boolean, default=False, index=True)
    permissions = Column(Integer)
    users = relationship('User', backref='role', lazy='dynamic')

    def __init__(self, name: str, permissions=None, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0
        self.name = name
        self.permissions = permissions

    @staticmethod
    def insert_roles():
        roles = {
            'USER': [Permission.USE],
            'ADMIN': [Permission.USE, Permission.BROADCAST,
                      Permission.SETTINGS_MANAGE, Permission.USERS_MANAGE, Permission.SHOP_MANAGE],
            'OWNER': [Permission.USE, Permission.BROADCAST,
                      Permission.SETTINGS_MANAGE, Permission.USERS_MANAGE, Permission.SHOP_MANAGE,
                      Permission.ADMINS_MANAGE, Permission.OWN],
        }
        default_role = 'USER'
        with Database().session() as s:
            for r, perms in roles.items():
                role = s.query(Role).filter_by(name=r).first()
                if role is None:
                    role = Role(name=r)
                    s.add(role)
                role.reset_permissions()
                for perm in perms:
                    role.add_permission(perm)
                role.default = (role.name == default_role)

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name


class User(Database.BASE):
    __tablename__ = 'users'
    telegram_id = Column(BigInteger, primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete="RESTRICT"), default=1, index=True)
    referral_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="SET NULL"), nullable=True, index=True)
    registration_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_banned = Column(Boolean, nullable=False, default=False, index=True)
    banned_at = Column(DateTime(timezone=True), nullable=True)
    banned_by = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="SET NULL"), nullable=True)
    ban_reason = Column(Text, nullable=True)
    user_goods = relationship("BoughtGoods", back_populates="user_telegram_id")

    referral_earnings_received = relationship(
        "ReferralEarnings",
        foreign_keys=lambda: [ReferralEarnings.referrer_id],
        back_populates="referrer"
    )
    referral_earnings_generated = relationship(
        "ReferralEarnings",
        foreign_keys=lambda: [ReferralEarnings.referral_id],
        back_populates="referral"
    )

    def __init__(self, telegram_id: int, registration_date: datetime.datetime, referral_id=None,
                 role_id: int = 1, is_banned: bool = False, banned_at=None, banned_by=None,
                 ban_reason: str = None, **kw: Any):
        super().__init__(**kw)
        self.telegram_id = telegram_id
        self.role_id = role_id
        self.referral_id = referral_id
        self.registration_date = registration_date
        self.is_banned = is_banned
        self.banned_at = banned_at
        self.banned_by = banned_by
        self.ban_reason = ban_reason


class Categories(Database.BASE):
    __tablename__ = 'categories'
    name = Column(String(100), primary_key=True)
    item = relationship("Goods", back_populates="category")

    def __init__(self, name: str, **kw: Any):
        super().__init__(**kw)
        self.name = name


class Goods(Database.BASE):
    __tablename__ = 'goods'
    name = Column(String(100), primary_key=True)
    price = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=False)
    category_name = Column(String(100), ForeignKey('categories.name', ondelete="CASCADE", onupdate="CASCADE"),
                           nullable=False, index=True)
    stock_quantity = Column(Integer, nullable=False, default=0)  # Total stock in warehouse
    reserved_quantity = Column(Integer, nullable=False, default=0)  # Reserved in pending orders
    category = relationship("Categories", back_populates="item")

    @property
    def available_quantity(self) -> int:
        """Calculate available stock (total - reserved)"""
        return max(0, self.stock_quantity - self.reserved_quantity)

    def __init__(self, name: str, price, description: str, category_name: str,
                 stock_quantity: int = 0, **kw: Any):
        super().__init__(**kw)
        self.name = name
        self.price = price
        self.description = description
        self.category_name = category_name
        self.stock_quantity = stock_quantity


class BoughtGoods(Database.BASE):
    __tablename__ = 'bought_goods'
    id = Column(Integer, primary_key=True)
    item_name = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    buyer_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="SET NULL"), nullable=True, index=True)
    bought_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    unique_id = Column(BigInteger, nullable=False, unique=True)
    user_telegram_id = relationship("User", back_populates="user_goods")

    def __init__(self, name: str, value: str, price, bought_datetime, unique_id, buyer_id: int = 0, **kw: Any):
        super().__init__(**kw)
        self.item_name = name
        self.value = value
        self.price = price
        self.buyer_id = buyer_id
        self.bought_datetime = bought_datetime
        self.unique_id = unique_id


class Operations(Database.BASE):
    __tablename__ = 'operations'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="CASCADE"), nullable=False, index=True)
    operation_value = Column(Numeric(12, 2), nullable=False)
    operation_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user_telegram_id = relationship("User")

    def __init__(self, user_id: int, operation_value, operation_time, **kw: Any):
        super().__init__(**kw)
        self.user_id = user_id
        self.operation_value = operation_value
        self.operation_time = operation_time


class ReferralEarnings(Database.BASE):
    __tablename__ = 'referral_earnings'

    id = Column(Integer, primary_key=True)
    referrer_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="CASCADE"), nullable=False)
    referral_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="CASCADE"),
                         nullable=True)  # NULL for admin bonuses
    amount = Column(Numeric(12, 2), nullable=False)
    original_amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    referrer = relationship(
        "User",
        foreign_keys=lambda: [ReferralEarnings.referrer_id],
        back_populates="referral_earnings_received"
    )
    referral = relationship(
        "User",
        foreign_keys=lambda: [ReferralEarnings.referral_id],
        back_populates="referral_earnings_generated"
    )

    __table_args__ = (
        Index('ix_referral_earnings_referrer_created', 'referrer_id', 'created_at'),
        Index('ix_referral_earnings_referral_created', 'referral_id', 'created_at'),
    )

    def __init__(self, referrer_id: int, referral_id: int | None, amount, original_amount, **kw: Any):
        super().__init__(**kw)
        self.referrer_id = referrer_id
        self.referral_id = referral_id
        self.amount = amount
        self.original_amount = original_amount


class ReferenceCode(Database.BASE):
    __tablename__ = 'reference_codes'

    code = Column(String(8), primary_key=True)
    created_by = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_uses = Column(Integer, nullable=True)  # None means unlimited
    current_uses = Column(Integer, nullable=False, default=0)
    note = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_admin_code = Column(Boolean, nullable=False, default=False)

    creator = relationship("User", foreign_keys=lambda: [ReferenceCode.created_by])
    usages = relationship("ReferenceCodeUsage", back_populates="reference_code", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_reference_codes_active_expires', 'is_active', 'expires_at'),
    )

    def __init__(self, code: str, created_by: int, expires_at=None, max_uses=None, note=None,
                 is_admin_code=False, **kw: Any):
        super().__init__(**kw)
        self.code = code
        self.created_by = created_by
        self.expires_at = expires_at
        self.max_uses = max_uses
        self.note = note
        self.is_admin_code = is_admin_code


class ReferenceCodeUsage(Database.BASE):
    __tablename__ = 'reference_code_usages'

    id = Column(Integer, primary_key=True)
    code = Column(String(8), ForeignKey('reference_codes.code', ondelete="CASCADE"), nullable=False, index=True)
    used_by = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="CASCADE"), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    reference_code = relationship("ReferenceCode", back_populates="usages")
    user = relationship("User", foreign_keys=lambda: [ReferenceCodeUsage.used_by])

    __table_args__ = (
        UniqueConstraint('code', 'used_by', name='uq_code_user'),
        Index('ix_reference_code_usages_used_at', 'used_at'),
    )

    def __init__(self, code: str, used_by: int, **kw: Any):
        super().__init__(**kw)
        self.code = code
        self.used_by = used_by


class Order(Database.BASE):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    order_code = Column(String(6), unique=True, nullable=True)  # Unique 6-char code (e.g., ECBDJI)
    buyer_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="SET NULL"), nullable=True, index=True)
    total_price = Column(Numeric(12, 2), nullable=False)
    bonus_applied = Column(Numeric(12, 2), nullable=True, default=0)  # Referral bonus applied to this order
    payment_method = Column(String(20), nullable=False)  # 'bitcoin' or 'cash'
    delivery_address = Column(Text, nullable=False)
    phone_number = Column(String(50), nullable=False)
    delivery_note = Column(Text, nullable=True)
    bitcoin_address = Column(String(100), nullable=True)
    order_status = Column(String(20), nullable=False,
                          default='pending')  # pending, reserved, confirmed, delivered, cancelled, expired
    reserved_until = Column(DateTime(timezone=True),
                            nullable=True)  # Reservation expiration time (configurable timeout)
    delivery_time = Column(DateTime(timezone=True), nullable=True)  # Planned delivery time set by admin
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    buyer = relationship("User", foreign_keys=lambda: [Order.buyer_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_orders_buyer_status', 'buyer_id', 'order_status'),
        Index('ix_orders_created_at', 'created_at'),
        Index('ix_orders_order_code', 'order_code'),
        Index('ix_orders_reserved_until', 'reserved_until'),  # For cleanup task
    )

    def __init__(self, buyer_id: int, total_price, payment_method: str,
                 delivery_address: str, phone_number: str, delivery_note: str = None,
                 bitcoin_address: str = None, order_status: str = 'pending',
                 order_code: str = None, reserved_until=None, delivery_time=None,
                 bonus_applied=0, **kw: Any):
        super().__init__(**kw)
        self.buyer_id = buyer_id
        self.order_code = order_code
        self.total_price = total_price
        self.bonus_applied = bonus_applied
        self.payment_method = payment_method
        self.delivery_address = delivery_address
        self.phone_number = phone_number
        self.delivery_note = delivery_note
        self.bitcoin_address = bitcoin_address
        self.order_status = order_status
        self.reserved_until = reserved_until
        self.delivery_time = delivery_time


class OrderItem(Database.BASE):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete="CASCADE"), nullable=False)
    item_name = Column(String(100), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)  # Price per unit
    quantity = Column(Integer, nullable=False, default=1)

    order = relationship("Order", back_populates="items")

    __table_args__ = (
        Index('ix_order_items_order_id', 'order_id'),
    )

    def __init__(self, order_id: int, item_name: str, price, quantity: int = 1, **kw: Any):
        super().__init__(**kw)
        self.order_id = order_id
        self.item_name = item_name
        self.price = price
        self.quantity = quantity


class CustomerInfo(Database.BASE):
    __tablename__ = 'customer_info'

    telegram_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="CASCADE"), primary_key=True)
    phone_number = Column(String(50), nullable=True)
    delivery_address = Column(Text, nullable=True)
    delivery_note = Column(Text, nullable=True)
    total_spendings = Column(Numeric(12, 2), nullable=False, default=0)
    completed_orders_count = Column(Integer, nullable=False, default=0)
    bonus_balance = Column(Numeric(12, 2), nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=lambda: [CustomerInfo.telegram_id])

    def __init__(self, telegram_id: int, phone_number: str = None, delivery_address: str = None,
                 delivery_note: str = None, **kw: Any):
        super().__init__(**kw)
        self.telegram_id = telegram_id
        self.phone_number = phone_number
        self.delivery_address = delivery_address
        self.delivery_note = delivery_note
        # Explicitly initialize numeric fields to prevent None values
        if not hasattr(self, 'total_spendings') or self.total_spendings is None:
            self.total_spendings = Decimal('0')
        if not hasattr(self, 'completed_orders_count') or self.completed_orders_count is None:
            self.completed_orders_count = 0
        if not hasattr(self, 'bonus_balance') or self.bonus_balance is None:
            self.bonus_balance = Decimal('0')


class BitcoinAddress(Database.BASE):
    __tablename__ = 'bitcoin_addresses'

    address = Column(String(100), primary_key=True)
    is_used = Column(Boolean, nullable=False, default=False, index=True)
    used_by = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="SET NULL"), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete="SET NULL"), nullable=True)

    user = relationship("User", foreign_keys=lambda: [BitcoinAddress.used_by])
    order = relationship("Order", foreign_keys=lambda: [BitcoinAddress.order_id])

    def __init__(self, address: str, **kw: Any):
        super().__init__(**kw)
        self.address = address


class BotSettings(Database.BASE):
    __tablename__ = 'bot_settings'

    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __init__(self, setting_key: str, setting_value: str = None, **kw: Any):
        super().__init__(**kw)
        self.setting_key = setting_key
        self.setting_value = setting_value


class ShoppingCart(Database.BASE):
    __tablename__ = 'shopping_cart'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="CASCADE"), nullable=False)
    item_name = Column(String(100), ForeignKey('goods.name', ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    added_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", foreign_keys=lambda: [ShoppingCart.user_id])
    item = relationship("Goods", foreign_keys=lambda: [ShoppingCart.item_name])

    __table_args__ = (
        UniqueConstraint('user_id', 'item_name', name='uq_cart_user_item'),
        Index('ix_shopping_cart_user_added', 'user_id', 'added_at'),
    )

    def __init__(self, user_id: int, item_name: str, quantity: int = 1, **kw: Any):
        super().__init__(**kw)
        self.user_id = user_id
        self.item_name = item_name
        self.quantity = quantity


class InventoryLog(Database.BASE):
    __tablename__ = 'inventory_log'

    id = Column(Integer, primary_key=True)
    item_name = Column(String(100), ForeignKey('goods.name', ondelete="CASCADE"), nullable=False)
    change_type = Column(String(20), nullable=False)  # reserve, release, deduct, add, manual, expired
    quantity_change = Column(Integer, nullable=False)  # Can be negative or positive
    order_id = Column(Integer, ForeignKey('orders.id', ondelete="SET NULL"), nullable=True, index=True)
    admin_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    comment = Column(Text, nullable=True)

    item = relationship("Goods", foreign_keys=lambda: [InventoryLog.item_name])
    order = relationship("Order", foreign_keys=lambda: [InventoryLog.order_id])
    admin = relationship("User", foreign_keys=lambda: [InventoryLog.admin_id])

    __table_args__ = (
        Index('ix_inventory_log_item_timestamp', 'item_name', 'timestamp'),
        Index('ix_inventory_log_type_timestamp', 'change_type', 'timestamp'),
    )

    def __init__(self, item_name: str, change_type: str, quantity_change: int,
                 order_id: int = None, admin_id: int = None, comment: str = None, **kw: Any):
        super().__init__(**kw)
        self.item_name = item_name
        self.change_type = change_type
        self.quantity_change = quantity_change
        self.order_id = order_id
        self.admin_id = admin_id
        self.comment = comment


def register_models():
    """Create all database tables and insert default roles"""
    import logging
    import time
    from sqlalchemy.exc import OperationalError

    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            db = Database()
            logging.info(f"Creating database tables (attempt {attempt}/{max_retries})...")
            Database.BASE.metadata.create_all(db.engine)

            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logging.info(f"Tables created successfully: {tables}")

            # Insert default roles
            Role.insert_roles()
            logging.info("Default roles inserted")
            return  # Success - exit function

        except OperationalError as e:
            # Retry on transient startup errors: DNS not resolvable yet AND the
            # DB accepting connections yet (compose brings Postgres up in parallel,
            # so "connection refused" / "starting up" races are expected).
            msg = str(e).lower()
            transient_markers = (
                "could not translate host name",
                "temporary failure in name resolution",
                "connection refused",
                "could not connect to server",
                "the database system is starting up",
                "timeout expired",
                "connection timed out",
            )
            if any(marker in msg for marker in transient_markers):
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff: 2s, 4s, 8s, 16s
                    logging.warning(
                        f"Database connection failed (attempt {attempt}/{max_retries}): {e}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                else:
                    logging.error(
                        f"Failed to connect to database after {max_retries} attempts. "
                        f"Please check if PostgreSQL container is running and network is configured correctly.",
                        exc_info=True
                    )
                    raise
            else:
                # Different OperationalError - raise immediately
                logging.error(f"Database operational error: {e}", exc_info=True)
                raise
        except Exception as e:
            logging.error(f"Failed to create database tables: {e}", exc_info=True)
            raise
