"""
Layer "Raw -> Core": baca file mentah (yang sudah ada di MinIO) baris demi
baris, standardisasi tipe data, simpan ke tabel core_transactions.

Ini processor PERTAMA (Pilot #1), dirancang untuk satu bentuk skema yang
sering muncul di data retail/marketplace/warung/POS: order_id, tanggal,
waktu, product_id, produk, kategori, qty, harga_satuan, subtotal, status.
Kalau nanti ada jenis dataset lain dengan kolom yang beda jauh (misal data
appointment klinik), processor ini TIDAK otomatis cocok — butuh processor
baru atau mapping kolom yang bisa dikonfigurasi per dataset. Itu sengaja
belum dibangun sekarang supaya tidak over-engineering untuk skema yang belum
pernah dilihat nyata.

Idempotent: process_dataset() selalu hapus dulu core_transactions milik
batch yang diproses ulang, baru insert lagi -- supaya dataset yang sama
boleh di-"Process Data" berkali-kali tanpa data dobel.
"""
import csv
import io
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models import Batch, CoreTransaction, Dataset, File
from app.models.core_transaction import REVENUE_STATUSES
from app.storage import minio_client

# Mapping nama kolom mentah (lowercased, di-strip) -> field CoreTransaction.
# Ditulis sebagai beberapa alias per field supaya sedikit lebih toleran
# terhadap variasi penamaan antar sumber data.
COLUMN_ALIASES = {
    "order_id": "order_id",
    "id_order": "order_id",
    "tanggal": "transaction_date",
    "date": "transaction_date",
    "waktu": "transaction_time",
    "time": "transaction_time",
    "product_id": "product_id",
    "id_produk": "product_id",
    "produk": "product_name",
    "product": "product_name",
    "nama_produk": "product_name",
    "kategori": "category",
    "category": "category",
    "qty": "qty",
    "quantity": "qty",
    "jumlah": "qty",
    "harga_satuan": "unit_price",
    "unit_price": "unit_price",
    "harga": "unit_price",
    "subtotal": "subtotal",
    "total": "subtotal",
    "status": "status_raw",
}


class UnrecognizedSchemaError(Exception):
    """Raised kalau file tidak punya kolom yang cukup untuk diproses (misal
    skema dataset yang berbeda jauh dari asumsi Pilot #1)."""


def process_dataset(db: Session, dataset_id) -> dict:
    """Proses ULANG semua batch berstatus 'success' milik satu dataset.
    Return ringkasan hasil: jumlah baris mentah, baris bersih yang tersimpan,
    baris duplikat (order_id sama dalam 1 batch), baris invalid (tanggal
    atau subtotal gagal di-parse) — dipakai langsung oleh step "Bersihkan
    Data" & "Validasi" di pipeline testing Laboratorium, bukan angka karangan.
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise ValueError("Dataset tidak ditemukan")

    batches = (
        db.query(Batch)
        .filter(Batch.dataset_id == dataset_id, Batch.status == "success")
        .all()
    )

    summary = {
        "batches_processed": 0,
        "rows_total": 0,
        "rows_written": 0,
        "duplicate_count": 0,
        "invalid_count": 0,
        "batches_skipped": [],
    }

    for batch in batches:
        try:
            stats = _process_batch(db, batch)
            summary["batches_processed"] += 1
            summary["rows_total"] += stats["rows_total"]
            summary["rows_written"] += stats["rows_written"]
            summary["duplicate_count"] += stats["duplicate_count"]
            summary["invalid_count"] += stats["invalid_count"]
        except UnrecognizedSchemaError as exc:
            summary["batches_skipped"].append({"batch_id": str(batch.id), "reason": str(exc)})

    db.commit()
    return summary


def _process_batch(db: Session, batch: Batch) -> dict:
    # Idempotent: buang dulu hasil proses lama untuk batch ini.
    db.query(CoreTransaction).filter(CoreTransaction.batch_id == batch.id).delete()

    file_row = db.query(File).filter(File.batch_id == batch.id).first()
    if file_row is None:
        raise UnrecognizedSchemaError("Batch tidak punya file mentah terkait.")

    raw_bytes = minio_client.get_file(file_row.storage_path)
    ext = file_row.filename.lower().rsplit(".", 1)[-1]

    if ext == "csv":
        rows = _read_csv_rows(raw_bytes)
    elif ext == "xlsx":
        rows = _read_xlsx_rows(raw_bytes)
    else:
        raise UnrecognizedSchemaError(f"Ekstensi '{ext}' belum didukung processor ini.")

    empty_stats = {"rows_total": 0, "rows_written": 0, "duplicate_count": 0, "invalid_count": 0}
    if not rows:
        return empty_stats

    header = [str(h or "").strip().lower() for h in rows[0]]
    field_by_col_index = {
        i: COLUMN_ALIASES[h] for i, h in enumerate(header) if h in COLUMN_ALIASES
    }

    # Minimal butuh subtotal & status supaya insight revenue punya arti —
    # kalau tidak ada sama sekali, ini kemungkinan besar skema yang beda.
    mapped_fields = set(field_by_col_index.values())
    if "subtotal" not in mapped_fields and "status_raw" not in mapped_fields:
        raise UnrecognizedSchemaError(
            "Kolom 'subtotal' dan 'status' tidak ditemukan — skema file ini "
            "kemungkinan beda dari yang didukung processor Pilot #1."
        )

    written = 0
    rows_total = 0
    duplicate_count = 0
    invalid_count = 0
    seen_order_ids: set[str] = set()

    for raw_row in rows[1:]:
        if not any(c not in (None, "") for c in raw_row):
            continue  # baris kosong, lewati — tidak dihitung rows_total sama sekali

        rows_total += 1

        values: dict = {}
        for i, cell in enumerate(raw_row):
            field = field_by_col_index.get(i)
            if field is None:
                continue
            values[field] = cell

        order_id = _clean_str(values.get("order_id"))
        if order_id is not None:
            if order_id in seen_order_ids:
                duplicate_count += 1
            seen_order_ids.add(order_id)

        transaction_date = _parse_date(values.get("transaction_date"))
        subtotal = _parse_decimal(values.get("subtotal"))
        # Invalid = kolom tanggal/subtotal ADA di file (termapping) tapi
        # nilainya gagal di-parse — beda dari kolom yang memang tidak ada.
        row_invalid = (
            "transaction_date" in mapped_fields
            and values.get("transaction_date") not in (None, "")
            and transaction_date is None
        ) or (
            "subtotal" in mapped_fields
            and values.get("subtotal") not in (None, "")
            and subtotal is None
        )
        if row_invalid:
            invalid_count += 1

        core_row = CoreTransaction(
            dataset_id=batch.dataset_id,
            batch_id=batch.id,
            order_id=order_id,
            transaction_date=transaction_date,
            transaction_time=_clean_str(values.get("transaction_time")),
            product_id=_clean_str(values.get("product_id")),
            product_name=_clean_str(values.get("product_name")),
            category=_clean_str(values.get("category")),
            qty=_parse_int(values.get("qty")),
            unit_price=_parse_decimal(values.get("unit_price")),
            subtotal=subtotal,
            status_raw=_clean_str(values.get("status_raw")),
            is_revenue=_is_revenue_status(values.get("status_raw")),
        )
        db.add(core_row)
        written += 1

    return {
        "rows_total": rows_total,
        "rows_written": written,
        "duplicate_count": duplicate_count,
        "invalid_count": invalid_count,
    }


def _read_csv_rows(raw_bytes: bytes) -> list[list]:
    text = raw_bytes.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def _read_xlsx_rows(raw_bytes: bytes) -> list[list]:
    wb = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    try:
        sheet = wb.active
        return [list(row) for row in sheet.iter_rows(values_only=True)]
    finally:
        wb.close()


def _clean_str(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _parse_int(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _parse_decimal(value) -> Decimal | None:
    try:
        if value is None or value == "":
            return None
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _is_revenue_status(status_raw) -> bool:
    if not status_raw:
        return False
    return str(status_raw).strip().lower() in REVENUE_STATUSES
