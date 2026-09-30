import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Divalidasi di layer API (bukan Postgres ENUM), sama seperti PROJECT_TIERS.
IDEA_STATUSES = ("baru", "dipakai")


class KompasIdea(Base):
    """Bank ide konten: satu baris = satu ide. status 'baru' = siap dipakai,
    'dipakai' = sudah dijadikan konten (used_at mencatat kapan)."""

    __tablename__ = "kompas_ideas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="baru")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
