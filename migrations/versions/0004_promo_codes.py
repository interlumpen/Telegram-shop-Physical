"""add promo codes (tables + order columns)

Revision ID: 0004_promo_codes
Revises: 0003_goods_sale
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_promo_codes"
down_revision = "0003_goods_sale"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("code", sa.String(length=32), primary_key=True),
        sa.Column("discount_type", sa.String(length=10), nullable=False),
        sa.Column("discount_value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("category_name", sa.String(length=100), nullable=True),
        sa.Column("item_name", sa.String(length=100), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("current_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.telegram_id"], ondelete="SET NULL"),
    )
    op.create_index("ix_promo_codes_is_active", "promo_codes", ["is_active"])
    op.create_index("ix_promo_codes_active_expires", "promo_codes", ["is_active", "expires_at"])

    op.create_table(
        "promo_code_usages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("used_by", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["code"], ["promo_codes.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["used_by"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("code", "used_by", name="uq_promo_code_user"),
    )
    op.create_index("ix_promo_code_usages_code", "promo_code_usages", ["code"])
    op.create_index("ix_promo_code_usages_used_by", "promo_code_usages", ["used_by"])

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(sa.Column("promo_code", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("promo_discount", sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("promo_discount")
        batch_op.drop_column("promo_code")

    op.drop_index("ix_promo_code_usages_used_by", table_name="promo_code_usages")
    op.drop_index("ix_promo_code_usages_code", table_name="promo_code_usages")
    op.drop_table("promo_code_usages")
    op.drop_index("ix_promo_codes_active_expires", table_name="promo_codes")
    op.drop_index("ix_promo_codes_is_active", table_name="promo_codes")
    op.drop_table("promo_codes")
