import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LabEntry(Base):
    """
    Catatan eksperimen MENTAH — ruang tampung sebelum sesuatu resmi jadi
    Project. TIDAK muncul di registry Proyek (01/02/03) sama sekali sampai
    kamu klik "Promosikan", yang baru saat itu membuat Project baru
    (tier=laboratorium) dari entri ini dan menghapus entri stagingnya.

    Beda dari Project: LabEntry tidak punya konsep "tier" — semuanya di sini
    memang belum berstatus proyek formal apa pun.
    """

    __tablename__ = "lab_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # List of {"label": str, "done": bool} — sama bentuknya dengan
    # Project.checklist supaya gampang di-copy saat promote.
    checklist: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True
    )
    # Dataset yang dipakai untuk pipeline testing (step Ambil Data dst di
    # halaman detail Laboratorium). Opsional karena entri boleh masih murni
    # ide tanpa data nyata sama sekali.
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    business: Mapped["Business | None"] = relationship()
    dataset: Mapped["Dataset | None"] = relationship()
