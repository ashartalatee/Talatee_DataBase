import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Setiap source milik satu business (klien) — ditambahkan saat platform
    # berkembang jadi multi-klien (Phase 2). Lihat migration & catatan di
    # ARCHITECTURE.md soal backfill data lama ke business default.
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    # misal "marketplace", "file_upload", "pos", "api"
    type: Mapped[str] = mapped_column(String, nullable=False)
    # "active" | "inactive"
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Trash (hapus sesaat). NULL = tidak dihapus. Diisi saat "Pindah ke
    # Sampah" lewat POST /sources/{id}/trash, dikosongkan lagi kalau
    # di-restore. Anak (datasets/batches) TIDAK ikut ditulis deleted_at-nya
    # saat parent di-trash — visibilitas dicek berantai lewat
    # app/services/trash.py (is_source_visible dkk), supaya restore parent
    # tanpa sengaja "menghidupkan" anak yang memang sengaja dihapus sendiri
    # tidak terjadi, dan restore anak independen tetap butuh parent-nya juga
    # tidak ter-trash. Baris ini TIDAK PERNAH benar-benar hilang dari DB
    # sampai ada aksi permanent-delete eksplisit (lihat deletion_log).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String, nullable=True)

    business: Mapped["Business"] = relationship(back_populates="sources")
    connectors: Mapped[list["Connector"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    datasets: Mapped[list["Dataset"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
