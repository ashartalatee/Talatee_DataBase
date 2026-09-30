import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KompasReview(Base):
    """Review mingguan: satu baris per minggu (week_start = hari Senin minggu itu).
    Tiga jawaban singkat. Unik per (username, week_start), jadi menyimpan ulang
    minggu yang sama memperbarui jawabannya, bukan membuat baris baru."""

    __tablename__ = "kompas_reviews"
    __table_args__ = (
        UniqueConstraint("username", "week_start", name="uq_kompas_review"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    built: Mapped[str] = mapped_column(Text, nullable=False, default="")
    improve: Mapped[str] = mapped_column(Text, nullable=False, default="")
    proud: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
