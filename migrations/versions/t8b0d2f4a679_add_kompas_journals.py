"""add kompas_journals table

Revision ID: t8b0d2f4a679
Revises: 9a578f7e06e8
Create Date: 2026-10-12 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 't8b0d2f4a679'
down_revision: Union[str, Sequence[str], None] = '9a578f7e06e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema (aditif: hanya tabel baru)."""
    op.create_table(
        'kompas_journals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('raw_transcript', sa.Text(), nullable=False),
        sa.Column('edited_text', sa.Text(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('send_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hooks', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('telegram_message_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('pending','processing','sent','failed')",
            name='ck_kompas_journals_status',
        ),
    )
    op.create_index('ix_kompas_journals_due', 'kompas_journals', ['status', 'send_at'])
    op.create_index('ix_kompas_journals_user_created', 'kompas_journals', ['username', 'created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_kompas_journals_user_created', table_name='kompas_journals')
    op.drop_index('ix_kompas_journals_due', table_name='kompas_journals')
    op.drop_table('kompas_journals')
