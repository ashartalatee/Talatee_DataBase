import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Reconciliation(Base):
    """
    Hasil pembanding "SOURCE TOTAL" (angka dari luar Talatee — misal dashboard
    marketplace/POS asli) vs "TALATEE TOTAL" (dihitung dari core_transactions
    yang is_revenue=True) untuk 1 periode (Data Trust Spec section 16).

    Ini snapshot HISTORIS — tidak diupdate. Kalau dataset diproses ulang atau
    dikoreksi, jalankan reconciliation lagi (POST) untuk dapat baris baru;
    baris lama tetap ada sebagai jejak audit "apa yang pernah dicek, kapan,
    hasilnya apa" (Rule 05: every important result must be traceable).

    Talatee TIDAK PERNAH otomatis mengklaim dataset "TRUSTED" berdasarkan
    reconciliation semata — ini pengecekan terpisah dan opsional (dataset
    bisa saja tidak punya angka pembanding dari luar), tidak masuk ke
    trust_status lifecycle (lihat Dataset.trust_status).
    """

    __tablename__ = "reconciliations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True
    )
    # Format "YYYY-MM" -- granularitas bulanan, konsisten dengan
    # revenue_by_month yang sudah ada di /insights.
    period_label: Mapped[str] = mapped_column(String, nullable=False, index=True)

    source_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    talatee_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    difference: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # PASSED | FAILED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dataset: Mapped["Dataset"] = relationship()
