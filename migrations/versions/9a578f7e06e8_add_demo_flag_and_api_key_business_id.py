"""add_demo_flag_and_api_key_business_id

Revision ID: 9a578f7e06e8
Revises: s7a9c1e3f568
Create Date: 2026-10-11 12:26:12.785167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a578f7e06e8'
down_revision: Union[str, Sequence[str], None] = 's7a9c1e3f568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'businesses',
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('api_keys', sa.Column('business_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_api_keys_business_id',
        'api_keys',
        'businesses',
        ['business_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_api_keys_business_id', 'api_keys', type_='foreignkey')
    op.drop_column('api_keys', 'business_id')
    op.drop_column('businesses', 'is_demo')
