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

DEDUP LINTAS DATASET (ditambahkan 4 September 2026 — lihat
PROJECT_CONTEXT_TALATEE.md bagian 6b/7): sebelumnya duplicate order_id cuma
dicek DALAM 1 batch (direset tiap batch), jadi upload ulang file yang sama
lolos tanpa terdeteksi dan bikin revenue di Analytics double-counted.
Sekarang seluruh batch di 1 dataset dibaca dulu (Pass 1), baru diputuskan
siapa "pemenang" tiap order_id sebelum ditulis (Pass 2). Kebijakan pemenang:
OKURENSI TERAKHIR menang (baik itu duplikat dalam 1 file yang sama, maupun
antar file/batch berbeda) — asumsi: upload ulang biasanya untuk memperbaiki
data lama, jadi versi paling akhir yang dianggap benar. Baris yang kalah
TIDAK ditulis ke core_transactions, tapi selalu dicatat di
summary["duplicates_skipped"] — sesuai Data Trust Spec section 9.4
("Duplicate tidak boleh langsung dihapus tanpa dicatat").

Batasan yang jujur perlu diketahui: kalau upload kedua BUKAN revisi tapi
order_id yang kebetulan dipakai ulang untuk transaksi lain (data bermasalah
di sumbernya), kebijakan "terakhir menang" ini bisa salah pilih baris.
Talatee belum punya correction model (section 14 spec) untuk kasus itu —
untuk sekarang, cek manual pakai scripts/investigate_duplicate_order_ids.py
kalau curiga ada kasus begini.
"""
import csv
import io
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models import Batch, CoreTransaction, Dataset, File, Correction, CORRECTABLE_FIELDS
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

    Dua tahap:
      Pass 1 — baca & urai SEMUA batch (urut waktu upload), tanpa nulis ke DB
               dulu, supaya bisa tahu order_id mana yang muncul lebih dari
               sekali SEBELUM memutuskan baris mana yang ditulis.
      Pass 2 — tulis ke core_transactions; baris "kalah" (order_id sudah
               dipakai baris yang lebih baru) di-skip, dicatat di
               duplicates_skipped, TIDAK dihapus diam-diam.

    Return ringkasan: rows_total (semua baris non-kosong di semua batch),
    rows_written (yang benar-benar masuk core_transactions), duplicate_count
    (yang di-skip karena kalah), invalid_count (tanggal/subtotal gagal
    parse — dihitung terlepas dari menang/kalah duplikat), duplicates_skipped
    (detail order_id + batch yang di-skip, untuk audit).
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise ValueError("Dataset tidak ditemukan")

    batches = (
        db.query(Batch)
        .filter(
            Batch.dataset_id == dataset_id,
            Batch.status == "success",
            # Batch yang lagi di-trash (hapus sesaat) dikecualikan dari
            # Raw->Core — lihat app/services/trash.py: trash_batch/
            # restore_batch memicu ulang process_dataset() supaya efeknya
            # langsung kelihatan di Analytics tanpa klik "Process Data".
            Batch.deleted_at.is_(None),
        )
        .order_by(Batch.started_at)
        .all()
    )

    summary = {
        "batches_processed": 0,
        "rows_total": 0,
        "rows_written": 0,
        "duplicate_count": 0,
        "invalid_count": 0,
        "corrections_applied": 0,
        "batches_skipped": [],
        "duplicates_skipped": [],
    }

    # ---- Pass 1: urai semua batch, ratakan jadi 1 urutan kronologis ----
    parsed_batches = []  # [(batch, file_row, [row_dict, ...]), ...]
    all_rows = []  # [(batch, file_row, row_dict), ...] urut sesuai upload

    for batch in batches:
        try:
            file_row, parsed_rows = _parse_batch(db, batch)
        except UnrecognizedSchemaError as exc:
            summary["batches_skipped"].append({"batch_id": str(batch.id), "reason": str(exc)})
            continue
        parsed_batches.append((batch, file_row, parsed_rows))
        for row in parsed_rows:
            all_rows.append((batch, file_row, row))

    # Okurensi TERAKHIR tiap order_id yang menang (lihat penjelasan
    # kebijakan di docstring modul).
    winner_index_for_order_id: dict[str, int] = {}
    for idx, (_batch, _file_row, row) in enumerate(all_rows):
        if row["order_id"] is not None:
            winner_index_for_order_id[row["order_id"]] = idx

    # Muat correction yang masih AKTIF (correction_version tertinggi per
    # order_id+field) sekali di awal, supaya Pass 2 tidak query berkali-kali
    # per baris (lihat Correction model utk kenapa dikunci ke order_id,
    # bukan core_transaction_id).
    active_corrections = _load_active_corrections(db, dataset_id)

    # ---- Pass 2: tulis, skip baris yang kalah ----
    idx = 0
    for batch, file_row, parsed_rows in parsed_batches:
        db.query(CoreTransaction).filter(CoreTransaction.batch_id == batch.id).delete()

        written = 0
        duplicate_count = 0
        invalid_count = 0

        for row in parsed_rows:
            if row["invalid"]:
                invalid_count += 1

            oid = row["order_id"]
            is_loser = oid is not None and winner_index_for_order_id[oid] != idx
            idx += 1

            if is_loser:
                duplicate_count += 1
                summary["duplicates_skipped"].append(
                    {
                        "order_id": oid,
                        "skipped_batch_id": str(batch.id),
                        "skipped_filename": file_row.filename,
                    }
                )
                continue

            row_values = dict(row)  # jangan mutasi dict asli di all_rows
            if oid is not None:
                for field in CORRECTABLE_FIELDS:
                    corrected_str = active_corrections.get((oid, field))
                    if corrected_str is not None:
                        row_values[field] = _cast_correction_value(field, corrected_str)
                        summary["corrections_applied"] += 1
                # status_raw bisa dikoreksi -> is_revenue harus dihitung ulang,
                # bukan dipakai dari hasil parsing RAW yang sudah usang.
                row_values["is_revenue"] = _is_revenue_status(row_values["status_raw"])

            db.add(
                CoreTransaction(
                    dataset_id=batch.dataset_id,
                    batch_id=batch.id,
                    order_id=oid,
                    transaction_date=row_values["transaction_date"],
                    transaction_time=row_values["transaction_time"],
                    product_id=row_values["product_id"],
                    product_name=row_values["product_name"],
                    category=row_values["category"],
                    qty=row_values["qty"],
                    unit_price=row_values["unit_price"],
                    subtotal=row_values["subtotal"],
                    status_raw=row_values["status_raw"],
                    is_revenue=row_values["is_revenue"],
                )
            )
            written += 1

        summary["batches_processed"] += 1
        summary["rows_total"] += len(parsed_rows)
        summary["rows_written"] += written
        summary["duplicate_count"] += duplicate_count
        summary["invalid_count"] += invalid_count

    db.commit()
    return summary


def _parse_batch(db: Session, batch: Batch) -> tuple[File, list[dict]]:
    """Baca 1 batch dari MinIO, urai jadi list row_dict SIAP TULIS —
    TANPA menyentuh DB (kecuali query baca File-nya). Dipisah dari langkah
    tulis supaya process_dataset() bisa lihat isi SEMUA batch dulu sebelum
    memutuskan siapa "pemenang" kalau ada order_id yang sama di lebih dari
    1 tempat."""
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

    if not rows:
        return file_row, []

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

    parsed_rows = []
    for raw_row in rows[1:]:
        if not any(c not in (None, "") for c in raw_row):
            continue  # baris kosong, lewati — tidak dihitung sama sekali

        values: dict = {}
        for i, cell in enumerate(raw_row):
            field = field_by_col_index.get(i)
            if field is None:
                continue
            values[field] = cell

        order_id = _clean_str(values.get("order_id"))
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

        parsed_rows.append(
            {
                "order_id": order_id,
                "transaction_date": transaction_date,
                "transaction_time": _clean_str(values.get("transaction_time")),
                "product_id": _clean_str(values.get("product_id")),
                "product_name": _clean_str(values.get("product_name")),
                "category": _clean_str(values.get("category")),
                "qty": _parse_int(values.get("qty")),
                "unit_price": _parse_decimal(values.get("unit_price")),
                "subtotal": subtotal,
                "status_raw": _clean_str(values.get("status_raw")),
                "is_revenue": _is_revenue_status(values.get("status_raw")),
                "invalid": row_invalid,
            }
        )

    return file_row, parsed_rows


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


def _load_active_corrections(db: Session, dataset_id) -> dict[tuple[str, str], str]:
    """Ambil correction yang masih AKTIF (correction_version tertinggi per
    order_id+field_name) untuk 1 dataset. Return dict {(order_id, field): nilai_string}.

    Diquery SEKALI di awal process_dataset() (bukan per-baris) supaya tidak
    N+1 query -- dataset skala personal biasanya cuma punya puluhan/ratusan
    correction, aman di-load semua ke memori sekaligus.
    """
    rows = (
        db.query(Correction)
        .filter(Correction.dataset_id == dataset_id)
        .order_by(Correction.correction_version.desc())
        .all()
    )
    active: dict[tuple[str, str], str] = {}
    for c in rows:
        key = (c.order_id, c.field_name)
        if key not in active:  # yang pertama ketemu = correction_version tertinggi
            active[key] = c.corrected_value
    return active


def _cast_correction_value(field_name: str, value_str: str):
    """Ubah nilai correction (selalu disimpan sebagai string di DB) balik ke
    tipe asli field-nya, pakai parser yang SAMA dengan yang dipakai saat
    parsing raw file -- supaya perilakunya konsisten (mis. format tanggal
    yang diterima sama persis)."""
    if field_name == "transaction_date":
        return _parse_date(value_str)
    if field_name == "qty":
        return _parse_int(value_str)
    if field_name in ("unit_price", "subtotal"):
        return _parse_decimal(value_str)
    return _clean_str(value_str)
