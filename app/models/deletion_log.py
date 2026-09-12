import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeletionLog(Base):
    """
    Jejak audit HAPUS PERMANEN. Baris di sini ditulis SEBELUM data aslinya
    benar-benar hilang dari DB/MinIO — supaya walaupun datanya sudah tidak
    ada, masih ada bukti "apa yang pernah ada, siapa yang hapus, kapan, dan
    kenapa" (konsisten dengan Rule 05: every important result must be
    traceable — dipakai di sini bukan untuk data transaksi tapi untuk
    tindakan penghapusannya sendiri).

    TIDAK PERNAH di-UPDATE atau DELETE lewat aplikasi. Level "source" |
    "dataset" | "batch" menandai di titik mana penghapusan permanen
    dipicu (untuk penghapusan berjenjang, cukup satu baris log di level
    yang diklik user — turunannya tidak masing-masing dapat baris sendiri,
    supaya log tidak banjir untuk satu aksi yang sama).
    """

    __tablename__ = "deletion_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    level: Mapped[str] = mapped_column(String, nullable=False)  # "source" | "dataset" | "batch"
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_name: Mapped[str] = mapped_column(String, nullable=False)
    # Path bergaris turun untuk konteks, misal "Resto Padang Jaya / Toko Kelontong / Orders"
    context_path: Mapped[str] = mapped_column(String, nullable=False)
    batches_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
