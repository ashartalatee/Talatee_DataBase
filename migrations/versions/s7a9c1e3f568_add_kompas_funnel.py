"""add kompas_funnel table

Revision ID: s7a9c1e3f568
Revises: r6f8b0d2e457
Create Date: 2026-10-01 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 's7a9c1e3f568'
down_revision: Union[str, Sequence[str], None] = 'r6f8b0d2e457'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('kompas_funnel',
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('stream', sa.String(), nullable=False),
    sa.Column('stage', sa.Integer(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('username', 'stream', 'stage'),
    sa.CheckConstraint('count >= 0', name='ck_kompas_funnel_count_nonneg'),
    sa.CheckConstraint('stage >= 0 AND stage <= 3', name='ck_kompas_funnel_stage_range'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('kompas_funnel')
