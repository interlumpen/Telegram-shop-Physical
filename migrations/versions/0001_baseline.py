"""baseline schema (state as of Phase 1)

Explicit, frozen snapshot of the schema created by the pre-Alembic
`metadata.create_all()`. It is deliberately NOT built from live metadata (that
would drift as new tables/columns are added to the models), so:
  * a fresh DB is built by upgrading through this revision, then later ones, and
  * an existing DB created by the old create_all() is stamped to this revision
    (see register_models()) without re-running any DDL.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('bot_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('setting_key', sa.String(length=100), nullable=False),
    sa.Column('setting_value', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('bot_settings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bot_settings_setting_key'), ['setting_key'], unique=True)

    op.create_table('categories',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('name')
    )
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('default', sa.Boolean(), nullable=True),
    sa.Column('permissions', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_roles_default'), ['default'], unique=False)

    op.create_table('goods',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('category_name', sa.String(length=100), nullable=False),
    sa.Column('stock_quantity', sa.Integer(), nullable=False),
    sa.Column('reserved_quantity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['category_name'], ['categories.name'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('name')
    )
    with op.batch_alter_table('goods', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_goods_category_name'), ['category_name'], unique=False)

    op.create_table('users',
    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=True),
    sa.Column('referral_id', sa.BigInteger(), nullable=True),
    sa.Column('registration_date', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('is_banned', sa.Boolean(), nullable=False),
    sa.Column('banned_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('banned_by', sa.BigInteger(), nullable=True),
    sa.Column('ban_reason', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['banned_by'], ['users.telegram_id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['referral_id'], ['users.telegram_id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('telegram_id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_is_banned'), ['is_banned'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_referral_id'), ['referral_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_role_id'), ['role_id'], unique=False)

    op.create_table('bought_goods',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_name', sa.String(length=100), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('buyer_id', sa.BigInteger(), nullable=True),
    sa.Column('bought_datetime', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('unique_id', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.telegram_id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('unique_id')
    )
    with op.batch_alter_table('bought_goods', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bought_goods_buyer_id'), ['buyer_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bought_goods_item_name'), ['item_name'], unique=False)

    op.create_table('customer_info',
    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
    sa.Column('phone_number', sa.String(length=50), nullable=True),
    sa.Column('delivery_address', sa.Text(), nullable=True),
    sa.Column('delivery_note', sa.Text(), nullable=True),
    sa.Column('total_spendings', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('completed_orders_count', sa.Integer(), nullable=False),
    sa.Column('bonus_balance', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['telegram_id'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('telegram_id')
    )
    op.create_table('operations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('operation_value', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('operation_time', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_operations_user_id'), ['user_id'], unique=False)

    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_code', sa.String(length=6), nullable=True),
    sa.Column('buyer_id', sa.BigInteger(), nullable=True),
    sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('bonus_applied', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('payment_method', sa.String(length=20), nullable=False),
    sa.Column('delivery_address', sa.Text(), nullable=False),
    sa.Column('phone_number', sa.String(length=50), nullable=False),
    sa.Column('delivery_note', sa.Text(), nullable=True),
    sa.Column('bitcoin_address', sa.String(length=100), nullable=True),
    sa.Column('order_status', sa.String(length=20), nullable=False),
    sa.Column('reserved_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delivery_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.telegram_id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('order_code')
    )
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_orders_buyer_id'), ['buyer_id'], unique=False)
        batch_op.create_index('ix_orders_buyer_status', ['buyer_id', 'order_status'], unique=False)
        batch_op.create_index('ix_orders_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_orders_order_code', ['order_code'], unique=False)
        batch_op.create_index('ix_orders_reserved_until', ['reserved_until'], unique=False)

    op.create_table('reference_codes',
    sa.Column('code', sa.String(length=8), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('max_uses', sa.Integer(), nullable=True),
    sa.Column('current_uses', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_admin_code', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('code')
    )
    with op.batch_alter_table('reference_codes', schema=None) as batch_op:
        batch_op.create_index('ix_reference_codes_active_expires', ['is_active', 'expires_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_reference_codes_created_by'), ['created_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_reference_codes_is_active'), ['is_active'], unique=False)

    op.create_table('referral_earnings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('referrer_id', sa.BigInteger(), nullable=False),
    sa.Column('referral_id', sa.BigInteger(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('original_amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['referral_id'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['referrer_id'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('referral_earnings', schema=None) as batch_op:
        batch_op.create_index('ix_referral_earnings_referral_created', ['referral_id', 'created_at'], unique=False)
        batch_op.create_index('ix_referral_earnings_referrer_created', ['referrer_id', 'created_at'], unique=False)

    op.create_table('shopping_cart',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('item_name', sa.String(length=100), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['item_name'], ['goods.name'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'item_name', name='uq_cart_user_item')
    )
    with op.batch_alter_table('shopping_cart', schema=None) as batch_op:
        batch_op.create_index('ix_shopping_cart_user_added', ['user_id', 'added_at'], unique=False)

    op.create_table('bitcoin_addresses',
    sa.Column('address', sa.String(length=100), nullable=False),
    sa.Column('is_used', sa.Boolean(), nullable=False),
    sa.Column('used_by', sa.BigInteger(), nullable=True),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['used_by'], ['users.telegram_id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('address')
    )
    with op.batch_alter_table('bitcoin_addresses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bitcoin_addresses_is_used'), ['is_used'], unique=False)

    op.create_table('inventory_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_name', sa.String(length=100), nullable=False),
    sa.Column('change_type', sa.String(length=20), nullable=False),
    sa.Column('quantity_change', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('admin_id', sa.BigInteger(), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['admin_id'], ['users.telegram_id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['item_name'], ['goods.name'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('inventory_log', schema=None) as batch_op:
        batch_op.create_index('ix_inventory_log_item_timestamp', ['item_name', 'timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_inventory_log_order_id'), ['order_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_inventory_log_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index('ix_inventory_log_type_timestamp', ['change_type', 'timestamp'], unique=False)

    op.create_table('order_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('item_name', sa.String(length=100), nullable=False),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.create_index('ix_order_items_order_id', ['order_id'], unique=False)

    op.create_table('reference_code_usages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=8), nullable=False),
    sa.Column('used_by', sa.BigInteger(), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['code'], ['reference_codes.code'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['used_by'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code', 'used_by', name='uq_code_user')
    )
    with op.batch_alter_table('reference_code_usages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reference_code_usages_code'), ['code'], unique=False)
        batch_op.create_index('ix_reference_code_usages_used_at', ['used_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_reference_code_usages_used_by'), ['used_by'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('reference_code_usages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reference_code_usages_used_by'))
        batch_op.drop_index('ix_reference_code_usages_used_at')
        batch_op.drop_index(batch_op.f('ix_reference_code_usages_code'))

    op.drop_table('reference_code_usages')
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_index('ix_order_items_order_id')

    op.drop_table('order_items')
    with op.batch_alter_table('inventory_log', schema=None) as batch_op:
        batch_op.drop_index('ix_inventory_log_type_timestamp')
        batch_op.drop_index(batch_op.f('ix_inventory_log_timestamp'))
        batch_op.drop_index(batch_op.f('ix_inventory_log_order_id'))
        batch_op.drop_index('ix_inventory_log_item_timestamp')

    op.drop_table('inventory_log')
    with op.batch_alter_table('bitcoin_addresses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bitcoin_addresses_is_used'))

    op.drop_table('bitcoin_addresses')
    with op.batch_alter_table('shopping_cart', schema=None) as batch_op:
        batch_op.drop_index('ix_shopping_cart_user_added')

    op.drop_table('shopping_cart')
    with op.batch_alter_table('referral_earnings', schema=None) as batch_op:
        batch_op.drop_index('ix_referral_earnings_referrer_created')
        batch_op.drop_index('ix_referral_earnings_referral_created')

    op.drop_table('referral_earnings')
    with op.batch_alter_table('reference_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reference_codes_is_active'))
        batch_op.drop_index(batch_op.f('ix_reference_codes_created_by'))
        batch_op.drop_index('ix_reference_codes_active_expires')

    op.drop_table('reference_codes')
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index('ix_orders_reserved_until')
        batch_op.drop_index('ix_orders_order_code')
        batch_op.drop_index('ix_orders_created_at')
        batch_op.drop_index('ix_orders_buyer_status')
        batch_op.drop_index(batch_op.f('ix_orders_buyer_id'))

    op.drop_table('orders')
    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_operations_user_id'))

    op.drop_table('operations')
    op.drop_table('customer_info')
    with op.batch_alter_table('bought_goods', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bought_goods_item_name'))
        batch_op.drop_index(batch_op.f('ix_bought_goods_buyer_id'))

    op.drop_table('bought_goods')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_role_id'))
        batch_op.drop_index(batch_op.f('ix_users_referral_id'))
        batch_op.drop_index(batch_op.f('ix_users_is_banned'))

    op.drop_table('users')
    with op.batch_alter_table('goods', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_goods_category_name'))

    op.drop_table('goods')
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_roles_default'))

    op.drop_table('roles')
    op.drop_table('categories')
    with op.batch_alter_table('bot_settings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bot_settings_setting_key'))

    op.drop_table('bot_settings')
