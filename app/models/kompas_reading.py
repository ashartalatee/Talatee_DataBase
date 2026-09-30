import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

READING_KINDS = ("artikel", "video")
DAILY_LIMIT = 3
VIDEO_HOSTS = ("youtube.com", "youtu.be", "tiktok.com", "vimeo.com")


def guess_kind(url: str) -> str:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return "video" if host.endswith(VIDEO_HOSTS) else "artikel"


class KompasReading(Base):
    """Bacaan terpilih. origin 'manual' = tautan yang kamu simpan sendiri,
    'auto' = kandidat dari sumber otomatis. planned_for = hari ia masuk daftar
    'hari ini' (maksimal DAILY_LIMIT per hari), read_at = kapan selesai dibaca,
    dismissed_at = dibuang/diganti (baris tetap ada supaya tidak muncul lagi)."""

    __tablename__ = "kompas_reading"
    __table_args__ = (UniqueConstraint("username", "url", name="uq_kompas_reading"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="artikel")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    planned_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    origin: Mapped[str] = mapped_column(String, nullable=False, default="manual", server_default="manual")
    source_name: Mapped[str | None] = mapped_column(String, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
