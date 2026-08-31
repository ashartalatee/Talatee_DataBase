import uuid
from datetime import datetime

from sqlalchemy import (
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Status yang dianggap "revenue nyata" (case-insensitive). Transaksi dengan
# status di luar daftar ini (misal Cancelled, Refunded, Pending) tetap
# tersimpan di tabel ini untuk keperluan audit, tapi tidak dihitung ke
# total revenue/growth. Daftar ini sengaja mencakup varian Indonesia &
# Inggris karena beda business/marketplace bisa pakai istilah beda.
REVENUE_STATUSES = {"completed", "success", "sukses", "berhasil", "paid", "lunas"}


class CoreTransaction(Base):
    """
    Baris transaksi yang SUDAH dibaca, di-parse, dan distandardisasi dari file
    mentah — bukan lagi sekadar metadata file. Ini "Layer Core" yang jadi
    dasar semua perhitungan insight (revenue, growth, top produk, dst).

    Dibuat oleh app/ingestion/core_processor.py, satu kali per batch. Kalau
    sebuah batch diproses ulang, baris lama untuk batch itu dihapus dulu
    (idempotent) supaya tidak dobel.

    Asumsi skema kolom mentah saat ini (Pilot #1 — data transaksi retail/
    marketplace/warung/POS): order_id, tanggal, waktu, product_id, produk,
    kategori, qty, harga_satuan, subtotal, status. Kalau nanti ada jenis data
    lain dengan skema beda (misal data klinik/appointment), butuh processor
    terpisah — lihat catatan di core_processor.py.
    """

    __tablename__ = "core_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False, index=True
    )

    order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date: Mapped[Date | None] = mapped_column(Date, nullable=True, index=True)
    transaction_time: Mapped[str | None] = mapped_column(String, nullable=True)
    product_id: Mapped[str | None] = mapped_column(String, nullable=True)
    product_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    subtotal: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    status_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    # True kalau status_raw (lowercased) ada di REVENUE_STATUSES — dihitung
    # sekali saat processing supaya query insight tidak perlu normalisasi
    # string berulang-ulang tiap kali.
    is_revenue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dataset: Mapped["Dataset"] = relationship()
    batch: Mapped["Batch"] = relationship()
