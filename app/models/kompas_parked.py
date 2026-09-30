import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# parkir -> (setelah masa tunggu) lolos -> eksperimen. Divalidasi di layer API.
PARKED_STATUSES = ("parkir", "lolos", "eksperimen")
COOLDOWN_DAYS = 30


class KompasParked(Base):
    """Parkir ide: ide bidang lain yang menggoda tapi tidak boleh langsung
    dikerjakan. review_on = tanggal paling awal ide boleh ditinjau ulang."""

    __tablename__ = "kompas_parked"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="parkir")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    review_on: Mapped[date] = mapped_column(Date, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
