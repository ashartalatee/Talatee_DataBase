import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Field yang boleh dikoreksi manual. Sengaja dibatasi (bukan "field apa saja
# di CoreTransaction") supaya korelasinya jelas ke business rule & quality
# check yang sudah ada — field administratif (order_id, batch_id, dataset_id)
# TIDAK boleh dikoreksi lewat mekanisme ini karena itu identitas baris, bukan
# nilai transaksi.
CORRECTABLE_FIELDS = {
    "transaction_date",
    "transaction_time",
    "product_id",
    "product_name",
    "category",
    "qty",
    "unit_price",
    "subtotal",
    "status_raw",
}


class Correction(Base):
    """
    Riwayat koreksi manual terhadap 1 field di 1 baris transaksi (Data Trust
    Spec section 14: "Correction tidak boleh menghapus history").

    PENTING — kenapa dikunci ke (dataset_id, order_id, field_name), BUKAN ke
    core_transaction_id: core_transactions di-generate ULANG setiap kali
    "Bersihkan Data" dijalankan (lihat core_processor.py) — baris lama
    dihapus, ID barunya beda. Kalau correction dikunci ke ID baris, correction
    akan HILANG begitu dataset diproses ulang. Dengan (dataset_id, order_id,
    field_name), core_processor.py bisa cari & terapkan ulang correction yang
    masih berlaku setiap kali proses ulang jalan — RAW tetap immutable (lihat
    _apply_corrections di core_processor.py), yang berubah cuma nilai di
    layer CANONICAL (core_transactions).

    Baris di tabel ini TIDAK PERNAH di-UPDATE atau DELETE — koreksi baru untuk
    field yang sama selalu INSERT baris baru dengan correction_version lebih
    tinggi. Yang "aktif"/dipakai adalah correction_version tertinggi per
    (dataset_id, order_id, field_name).

    Batasan yang jujur: order_id WAJIB ada di baris yang mau dikoreksi (baris
    tanpa order_id tidak bisa ditarget lewat mekanisme ini, karena tidak ada
    identitas stabil yang bertahan lintas proses ulang).
    """

    __tablename__ = "corrections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True
    )
    order_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String, nullable=False)

    # Disimpan sebagai string apa adanya (bukan tipe asli field-nya) supaya
    # 1 tabel bisa menampung koreksi utk field bertipe apa pun (tanggal,
    # angka, teks) — casting ke tipe asli dilakukan saat diterapkan di
    # core_processor.py, bukan di sini.
    original_value: Mapped[str | None] = mapped_column(String, nullable=True)
    corrected_value: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[str | None] = mapped_column(String, nullable=True)
    correction_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    corrected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dataset: Mapped["Dataset"] = relationship()
