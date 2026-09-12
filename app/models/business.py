import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Daftar tetap (dropdown), bukan free text — keputusan produk saat Phase 2 (Businesses).
# "warung", "laundry", "bengkel" ditambahkan supaya cocok dengan business_type yang
# sudah dirancang di produk vertikal "Buku Kas Warung" (lihat integrasi Talatee Bridge).
BUSINESS_CATEGORIES = [
    "restoran",
    "klinik",
    "marketplace",
    "retail",
    "warung",
    "laundry",
    "bengkel",
    "lainnya",
]


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    # salah satu dari BUSINESS_CATEGORIES (divalidasi di layer Pydantic/API,
    # bukan CHECK constraint DB — konsisten dengan sources.type/connectors.type
    # yang juga VARCHAR biasa)
    category: Mapped[str] = mapped_column(String, nullable=False, default="lainnya")
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Trash (hapus sesaat) — lihat catatan lengkap di Source.deleted_at.
    # Business adalah level PALING ATAS: trash di sini menyembunyikan
    # SEMUA source/dataset/batch di bawahnya juga (dicek berantai lewat
    # app/services/trash.py), walau baris anak-anaknya sendiri tidak
    # ditulis deleted_at-nya.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String, nullable=True)

    sources: Mapped[list["Source"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
