"""add businesses and source business_id

Revision ID: ffd9f70c7dae
Revises: 8efeb9074d19
Create Date: 2026-08-23 14:18:09.717464

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffd9f70c7dae'
down_revision: Union[str, Sequence[str], None] = '3f158c766bcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('businesses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    # 1) Tambah kolom business_id sebagai NULLABLE dulu — supaya row `sources`
    #    yang SUDAH ADA (data lama) tidak langsung error kena NOT NULL
    #    constraint saat kolomnya baru ditambahkan.
    op.add_column('sources', sa.Column('business_id', sa.UUID(), nullable=True))

    # 2) Buat 1 business default untuk menampung source lama yang belum
    #    dikategorikan. Keputusan produk: data lama TIDAK dihapus, otomatis
    #    masuk ke business "Belum Dikategorikan" (category="lainnya").
    default_business_id = str(uuid.uuid4())
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO businesses (id, name, category, status, created_at) "
            "VALUES (:id, :name, :category, :status, now())"
        ),
        {
            "id": default_business_id,
            "name": "Belum Dikategorikan",
            "category": "lainnya",
            "status": "active",
        },
    )

    # 3) Backfill semua source lama (business_id masih NULL) ke business default.
    conn.execute(
        sa.text("UPDATE sources SET business_id = :bid WHERE business_id IS NULL"),
        {"bid": default_business_id},
    )

    # 4) Baru sekarang aman di-set NOT NULL — semua row sudah pasti terisi.
    op.alter_column('sources', 'business_id', nullable=False)

    op.create_foreign_key(
        'fk_sources_business_id', 'sources', 'businesses', ['business_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_sources_business_id', 'sources', type_='foreignkey')
    op.drop_column('sources', 'business_id')
    op.drop_table('businesses')

