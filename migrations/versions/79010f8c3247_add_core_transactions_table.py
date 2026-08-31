"""add core_transactions table

Revision ID: 79010f8c3247
Revises: 7a2c9e5f3b41
Create Date: 2026-08-31 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79010f8c3247'
down_revision: Union[str, Sequence[str], None] = '7a2c9e5f3b41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('core_transactions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('dataset_id', sa.UUID(), nullable=False),
    sa.Column('batch_id', sa.UUID(), nullable=False),
    sa.Column('order_id', sa.String(), nullable=True),
    sa.Column('transaction_date', sa.Date(), nullable=True),
    sa.Column('transaction_time', sa.String(), nullable=True),
    sa.Column('product_id', sa.String(), nullable=True),
    sa.Column('product_name', sa.String(), nullable=True),
    sa.Column('category', sa.String(), nullable=True),
    sa.Column('qty', sa.Integer(), nullable=True),
    sa.Column('unit_price', sa.Numeric(14, 2), nullable=True),
    sa.Column('subtotal', sa.Numeric(14, 2), nullable=True),
    sa.Column('status_raw', sa.String(), nullable=True),
    sa.Column('is_revenue', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
    sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_core_transactions_dataset_id'), 'core_transactions', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_core_transactions_batch_id'), 'core_transactions', ['batch_id'], unique=False)
    op.create_index(op.f('ix_core_transactions_transaction_date'), 'core_transactions', ['transaction_date'], unique=False)
    op.create_index(op.f('ix_core_transactions_product_name'), 'core_transactions', ['product_name'], unique=False)
    op.create_index(op.f('ix_core_transactions_category'), 'core_transactions', ['category'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_core_transactions_category'), table_name='core_transactions')
    op.drop_index(op.f('ix_core_transactions_product_name'), table_name='core_transactions')
    op.drop_index(op.f('ix_core_transactions_transaction_date'), table_name='core_transactions')
    op.drop_index(op.f('ix_core_transactions_batch_id'), table_name='core_transactions')
    op.drop_index(op.f('ix_core_transactions_dataset_id'), table_name='core_transactions')
    op.drop_table('core_transactions')
