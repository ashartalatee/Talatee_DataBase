"""add kompas_parked table

Revision ID: n3c5e7a9b124
Revises: m2b4d6f8a013
Create Date: 2026-09-30 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n3c5e7a9b124'
down_revision: Union[str, Sequence[str], None] = 'm2b4d6f8a013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('kompas_parked',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('reason', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=False, server_default='parkir'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('review_on', sa.Date(), nullable=False),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_kompas_parked_username_status'), 'kompas_parked', ['username', 'status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_kompas_parked_username_status'), table_name='kompas_parked')
    op.drop_table('kompas_parked')
