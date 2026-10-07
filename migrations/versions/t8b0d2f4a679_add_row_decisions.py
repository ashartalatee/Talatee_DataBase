"""add row_decisions table

Revision ID: t8b0d2f4a679
Revises: s7a9c1e3f568
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "t8b0d2f4a679"
down_revision = "s7a9c1e3f568"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "row_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("column_name", sa.String(), nullable=True),
        sa.Column("old_value", sa.String(), nullable=True),
        sa.Column("new_value", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decided_by", sa.String(), nullable=True),
        sa.Column("decision_version", sa.Integer(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_row_decisions_batch_id", "row_decisions", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_row_decisions_batch_id", table_name="row_decisions")
    op.drop_table("row_decisions")
