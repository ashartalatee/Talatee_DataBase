"""add kompas_reading table

Revision ID: q5e7a9c1d346
Revises: p4d6f8b0c235
Create Date: 2026-09-30 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'q5e7a9c1d346'
down_revision: Union[str, Sequence[str], None] = 'p4d6f8b0c235'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('kompas_reading',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False, server_default='artikel'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('planned_for', sa.Date(), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username', 'url', name='uq_kompas_reading'),
    )
    op.create_index(op.f('ix_kompas_reading_username_planned'), 'kompas_reading', ['username', 'planned_for'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_kompas_reading_username_planned'), table_name='kompas_reading')
    op.drop_table('kompas_reading')
