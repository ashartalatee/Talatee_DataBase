"""add corrections and reconciliations tables

Revision ID: d4e8f1a2b3c9
Revises: b3f2a1c9d8e7
Create Date: 2026-09-05 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e8f1a2b3c9'
down_revision: Union[str, Sequence[str], None] = 'b3f2a1c9d8e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Dua tabel baru untuk menutup 2 gap Data Trust Spec yang masih terbuka:
    section 14 (Correction Model) dan section 16 (Reconciliation). Keduanya
    APPEND-ONLY -- tidak ada UPDATE/DELETE dari aplikasi, cuma INSERT --
    supaya riwayatnya tetap utuh sebagai bukti audit.
    """
    op.create_table(
        'corrections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id'), nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('field_name', sa.String(), nullable=False),
        sa.Column('original_value', sa.String(), nullable=True),
        sa.Column('corrected_value', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('corrected_by', sa.String(), nullable=True),
        sa.Column('correction_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('corrected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_corrections_dataset_id', 'corrections', ['dataset_id'])
    op.create_index('ix_corrections_order_id', 'corrections', ['order_id'])
    # Query paling sering: "cari correction TERBARU untuk (dataset, order_id,
    # field) ini" -- index gabungan ini yang dipakai core_processor.py.
    op.create_index(
        'ix_corrections_lookup',
        'corrections',
        ['dataset_id', 'order_id', 'field_name'],
    )

    op.create_table(
        'reconciliations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id'), nullable=False),
        sa.Column('period_label', sa.String(), nullable=False),
        sa.Column('source_total', sa.Numeric(14, 2), nullable=False),
        sa.Column('talatee_total', sa.Numeric(14, 2), nullable=False),
        sa.Column('difference', sa.Numeric(14, 2), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_reconciliations_dataset_id', 'reconciliations', ['dataset_id'])
    op.create_index('ix_reconciliations_period_label', 'reconciliations', ['period_label'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_reconciliations_period_label', table_name='reconciliations')
    op.drop_index('ix_reconciliations_dataset_id', table_name='reconciliations')
    op.drop_table('reconciliations')

    op.drop_index('ix_corrections_lookup', table_name='corrections')
    op.drop_index('ix_corrections_order_id', table_name='corrections')
    op.drop_index('ix_corrections_dataset_id', table_name='corrections')
    op.drop_table('corrections')
