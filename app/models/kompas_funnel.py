from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Jalur penghasilan di bagian Arah (Kompas). Kunci berupa nama, bukan nomor urut,
# supaya data tidak bergeser kalau urutan kartu di tampilan diubah.
FUNNEL_STREAMS = ("klien", "kerja", "retainer", "produk", "konten")
FUNNEL_STAGES = 4  # tiap jalur punya 4 tahap, indeks 0..3
MAX_COUNT = 100000


class KompasFunnel(Base):
    """Penghitung corong per pengguna, per jalur, per tahap. Satu baris = satu angka."""

    __tablename__ = "kompas_funnel"

    username: Mapped[str] = mapped_column(String, primary_key=True)
    stream: Mapped[str] = mapped_column(String, primary_key=True)
    stage: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("count >= 0", name="ck_kompas_funnel_count_nonneg"),
        CheckConstraint("stage >= 0 AND stage <= 3", name="ck_kompas_funnel_stage_range"),
    )
