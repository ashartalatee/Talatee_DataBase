"""add trash columns to businesses

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("businesses", sa.Column("deleted_by", sa.String(), nullable=True))
    op.create_index(op.f("ix_businesses_deleted_at"), "businesses", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_businesses_deleted_at"), table_name="businesses")
    op.drop_column("businesses", "deleted_by")
    op.drop_column("businesses", "deleted_at")
