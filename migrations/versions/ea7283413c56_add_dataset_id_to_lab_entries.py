"""add dataset_id to lab_entries and projects

Revision ID: ea7283413c56
Revises: c71a9d296d4d
Create Date: 2026-09-01 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea7283413c56'
down_revision: Union[str, Sequence[str], None] = 'c71a9d296d4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('lab_entries', sa.Column('dataset_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_lab_entries_dataset_id', 'lab_entries', 'datasets', ['dataset_id'], ['id']
    )
    op.add_column('projects', sa.Column('dataset_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_projects_dataset_id', 'projects', 'datasets', ['dataset_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_projects_dataset_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'dataset_id')
    op.drop_constraint('fk_lab_entries_dataset_id', 'lab_entries', type_='foreignkey')
    op.drop_column('lab_entries', 'dataset_id')
