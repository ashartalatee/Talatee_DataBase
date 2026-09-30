"""add kompas_reviews table

Revision ID: p4d6f8b0c235
Revises: n3c5e7a9b124
Create Date: 2026-09-30 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p4d6f8b0c235'
down_revision: Union[str, Sequence[str], None] = 'n3c5e7a9b124'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('kompas_reviews',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('week_start', sa.Date(), nullable=False),
    sa.Column('built', sa.Text(), nullable=False, server_default=''),
    sa.Column('improve', sa.Text(), nullable=False, server_default=''),
    sa.Column('proud', sa.Text(), nullable=False, server_default=''),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username', 'week_start', name='uq_kompas_review'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('kompas_reviews')
