"""add time-limited sale columns to goods

Revision ID: 0003_goods_sale
Revises: 0002_audit_log
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_goods_sale"
down_revision = "0002_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("goods", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sale_percent", sa.Numeric(precision=5, scale=2), nullable=True))
        batch_op.add_column(sa.Column("sale_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("goods", schema=None) as batch_op:
        batch_op.drop_column("sale_until")
        batch_op.drop_column("sale_percent")
