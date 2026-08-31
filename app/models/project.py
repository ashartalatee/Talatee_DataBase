import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# 3 tahap sesuai kerangka yang kamu tulis sendiri di dokumen visi:
# 01 Laboratorium (coba-coba), 02 Siap Publikasi (matang, siap demo),
# 03 Live (dipakai client nyata). Divalidasi di layer API (bukan Postgres
# ENUM) supaya gampang diubah kalau nanti butuh tahap baru.
PROJECT_TIERS = {"laboratorium", "siap_publikasi", "live"}


class Project(Base):
    """
    Registry proyek NYATA yang kamu isi & update sendiri dari dashboard —
    beda dari Business (yang datanya diisi otomatis dari upload/ingestion).
    Ini jawaban atas masalah berulang "tolong pindah X ke tier Y" yang
    sebelumnya harus saya hardcode manual di frontend tiap kali.

    business_id OPSIONAL: isi kalau proyek ini punya data client nyata yang
    mengalir ke Talatee (jadi kartunya bisa tampilkan jumlah records asli),
    kosongkan kalau proyek ini murni development (misal Buku Kas Warung
    sebelum ada client yang datanya masuk ke sini).
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    tier: Mapped[str] = mapped_column(String, nullable=False, default="laboratorium", index=True)
    status_note: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # List of {"label": str, "done": bool}
    checklist: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    deploy_target: Mapped[str | None] = mapped_column(String, nullable=True)

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    business: Mapped["Business | None"] = relationship()
