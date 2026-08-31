"""add projects table

Revision ID: f3e0bf05b984
Revises: 79010f8c3247
Create Date: 2026-08-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f3e0bf05b984'
down_revision: Union[str, Sequence[str], None] = '79010f8c3247'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('projects',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('tier', sa.String(), nullable=False),
    sa.Column('status_note', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('checklist', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('repo_url', sa.String(), nullable=True),
    sa.Column('deploy_target', sa.String(), nullable=True),
    sa.Column('business_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_projects_tier'), 'projects', ['tier'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_projects_tier'), table_name='projects')
    op.drop_table('projects')
