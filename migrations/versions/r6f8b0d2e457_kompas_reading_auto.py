"""kompas_reading: kolom untuk bacaan otomatis

Revision ID: r6f8b0d2e457
Revises: q5e7a9c1d346
Create Date: 2026-09-30 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'r6f8b0d2e457'
down_revision: Union[str, Sequence[str], None] = 'q5e7a9c1d346'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('kompas_reading', sa.Column('origin', sa.String(), nullable=False, server_default='manual'))
    op.add_column('kompas_reading', sa.Column('source_name', sa.String(), nullable=True))
    op.add_column('kompas_reading', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('kompas_reading', sa.Column('score', sa.Integer(), nullable=True))
    op.add_column('kompas_reading', sa.Column('expires_on', sa.Date(), nullable=True))
    op.add_column('kompas_reading', sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for col in ('dismissed_at', 'expires_on', 'score', 'published_at', 'source_name', 'origin'):
        op.drop_column('kompas_reading', col)
