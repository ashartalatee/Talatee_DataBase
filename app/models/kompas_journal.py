import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Divalidasi di layer API + CHECK constraint di migrasi, sama seperti pola Kompas lain.
JOURNAL_STATUSES = ("pending", "processing", "sent", "failed")
SEND_DELAY = timedelta(hours=3)  # hook dikirim 3 jam setelah jurnal DISIMPAN
MAX_ATTEMPTS = 6


class KompasJournal(Base):
    """Satu baris = satu jurnal suara.

    raw_transcript : hasil transkripsi asli, TIDAK PERNAH ditimpa (ucapan aslimu).
    edited_text    : versi yang sudah kamu koreksi, ini yang dibaca Hermes.
    status         : pending -> processing -> sent | failed. Satu jurnal hanya
                     bisa 'sent' sekali, jadi tidak ada notifikasi ganda.
    hooks          : 5 hook hasil Hermes (disimpan sebelum dikirim, jadi kalau
                     Telegram gagal, percobaan ulang tidak memanggil Hermes lagi).
    """

    __tablename__ = "kompas_journals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False)
    edited_text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hooks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
