"""add trust_status to datasets

Revision ID: b3f2a1c9d8e7
Revises: ea7283413c56
Create Date: 2026-09-04 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f2a1c9d8e7'
down_revision: Union[str, Sequence[str], None] = 'ea7283413c56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Tambah kolom trust_status ke datasets. server_default memastikan semua
    dataset LAMA otomatis dapat 'INGESTED' saat migration jalan (bukan NULL) —
    aman karena INGESTED memang status paling awal/konservatif, tidak ada
    dataset lama yang tiba-tiba "naik derajat" tanpa melalui proses semestinya.
    """
    op.add_column(
        'datasets',
        sa.Column('trust_status', sa.String(), nullable=False, server_default='INGESTED'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('datasets', 'trust_status')
