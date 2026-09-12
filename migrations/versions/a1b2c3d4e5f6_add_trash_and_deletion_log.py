"""add trash (soft delete) columns and deletion_logs table

Revision ID: a1b2c3d4e5f6
Revises: d4e8f1a2b3c9
Create Date: 2026-09-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'd4e8f1a2b3c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("sources", "datasets", "batches"):
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("deleted_by", sa.String(), nullable=True))
        op.create_index(op.f(f"ix_{table}_deleted_at"), table, ["deleted_at"], unique=False)

    op.create_table(
        "deletion_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_name", sa.String(), nullable=False),
        sa.Column("context_path", sa.String(), nullable=False),
        sa.Column("batches_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("deleted_by", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("deletion_logs")
    for table in ("sources", "datasets", "batches"):
        op.drop_index(op.f(f"ix_{table}_deleted_at"), table_name=table)
        op.drop_column(table, "deleted_by")
        op.drop_column(table, "deleted_at")
