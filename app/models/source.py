import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Setiap source milik satu business (klien) — ditambahkan saat platform
    # berkembang jadi multi-klien (Phase 2). Lihat migration & catatan di
    # ARCHITECTURE.md soal backfill data lama ke business default.
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    # misal "marketplace", "file_upload", "pos", "api"
    type: Mapped[str] = mapped_column(String, nullable=False)
    # "active" | "inactive"
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    business: Mapped["Business"] = relationship(back_populates="sources")
    connectors: Mapped[list["Connector"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    datasets: Mapped[list["Dataset"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
