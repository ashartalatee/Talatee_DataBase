"""add kompas_ideas table

Revision ID: m2b4d6f8a013
Revises: k7a1c3e5b902
Create Date: 2026-09-30 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'm2b4d6f8a013'
down_revision: Union[str, Sequence[str], None] = 'k7a1c3e5b902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('kompas_ideas',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False, server_default='baru'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_kompas_ideas_username_status'), 'kompas_ideas', ['username', 'status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_kompas_ideas_username_status'), table_name='kompas_ideas')
    op.drop_table('kompas_ideas')
