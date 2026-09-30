import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Tiga kebiasaan inti 2027. Divalidasi di layer API (bukan Postgres ENUM),
# sama seperti PROJECT_TIERS, supaya gampang diubah kalau nanti berubah.
KOMPAS_HABITS = ("project", "speaking", "content")


class KompasCheckin(Base):
    """Satu baris = satu kebiasaan yang dicentang selesai pada satu tanggal.
    Unik per (username, habit, day), jadi mencentang dua kali tidak bisa dobel."""

    __tablename__ = "kompas_checkins"
    __table_args__ = (
        UniqueConstraint("username", "habit", "day", name="uq_kompas_checkin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, nullable=False)
    habit: Mapped[str] = mapped_column(String, nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
