import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Trust status lifecycle (versi minimal — lihat PROJECT_CONTEXT_TALATEE.md /
# Data Trust Specification section 7 untuk versi lengkap yang lebih ambisius).
# Sengaja TIDAK mengimplementasikan seluruh state (CORRECTING, REVALIDATING,
# RECONCILING) karena fitur pendukungnya (correction model, reconciliation)
# belum ada — daripada bikin status yang tidak pernah kepakai.
#
# INGESTED      dataset baru / core_transactions belum pernah diproses
# VALIDATING    quality score sudah pernah dihitung, belum diputuskan
# NEEDS_REVIEW  quality check terakhir menghasilkan >=1 error
# TRUSTED       eksplisit di-promote lewat POST /datasets/{id}/promote —
#               TIDAK PERNAH otomatis walau quality_score tinggi (lihat
#               Data Trust Spec section 12: Trust Status != Data Quality Score)
TRUST_STATUSES = {"INGESTED", "VALIDATING", "NEEDS_REVIEW", "TRUSTED"}


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # schema hasil inferensi dari batch TERAKHIR (overwrite, bukan merge — keputusan Phase 1)
    schema_: Mapped[dict | None] = mapped_column("schema", JSONB, nullable=True)
    trust_status: Mapped[str] = mapped_column(
        String, nullable=False, default="INGESTED", server_default="INGESTED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Trash (hapus sesaat) — lihat catatan lengkap di Source.deleted_at,
    # perilakunya sama persis di level dataset.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String, nullable=True)

    source: Mapped["Source"] = relationship(back_populates="datasets")
    batches: Mapped[list["Batch"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
