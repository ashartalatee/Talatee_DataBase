"""add kompas_checkins table

Revision ID: k7a1c3e5b902
Revises: b2c3d4e5f6a7
Create Date: 2026-09-30 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k7a1c3e5b902'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('kompas_checkins',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('habit', sa.String(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username', 'habit', 'day', name='uq_kompas_checkin'),
    )
    op.create_index(op.f('ix_kompas_checkins_username_day'), 'kompas_checkins', ['username', 'day'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_kompas_checkins_username_day'), table_name='kompas_checkins')
    op.drop_table('kompas_checkins')
