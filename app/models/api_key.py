import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ApiKey(Base):
    """
    Key untuk autentikasi machine-to-machine (produk lain -> Talatee), BUKAN
    untuk login dashboard/user. Contoh: buku-kas-warung pakai 1 API key untuk
    semua request sync-nya, terlepas dari business_name mana yang dia kirim
    di tiap request (auto-create business tetap jalan seperti biasa — API key
    ini cuma membuktikan "request ini datang dari integrasi yang terdaftar",
    bukan membatasi ke satu business tertentu).

    key_hash menyimpan SHA-256 dari key asli. Key ASLI (plaintext) cuma
    ditampilkan SEKALI saat dibuat (lihat scripts/create_api_key.py) — tidak
    pernah disimpan/ditampilkan lagi setelah itu, sama seperti Stripe/GitHub
    token.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)  # misal "Buku Kas Warung"
    key_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)  # misal "tal_a1b2c3d4" — buat identifikasi di UI tanpa expose full key
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # "active" | "revoked"
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped["Business | None"] = relationship()
