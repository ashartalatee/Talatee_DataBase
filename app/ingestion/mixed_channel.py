"""
Mode "File ini campur beberapa channel" -- satu file upload berisi data dari
BEBERAPA channel sekaligus (dibedakan lewat kolom channel/platform/
marketplace/sumber, sama seperti channel_guard.py, tapi di sini kolom itu
WAJIB ADA -- beda dari channel_guard.py yang membuatnya opsional).

split_by_channel() memecah file itu jadi N file CSV terpisah (satu per nilai
channel unik yang ditemukan), masing-masing lengkap dengan header. Tiap
pecahan itu KEMUDIAN lewat IngestionEngine.ingest() yang SAMA PERSIS dengan
upload single-channel biasa (lihat app/api/routes/ingestion.py:
_run_mixed_ingest) -- jadi tidak ada jalur khusus di engine/core_processor/
trash/dst, semuanya otomatis kepakai tanpa perubahan.
"""
from app.ingestion.file_rows import CHANNEL_COLUMN_ALIASES, normalize_channel_value, read_rows
import csv
import io


class MixedChannelError(ValueError):
    """Raise kalau file tidak cocok dipakai di mode ini -- ditangkap route
    dan dikembalikan sebagai HTTP 400 (ini kesalahan permintaan yang
    fundamental, BUKAN kegagalan di dalam data seperti file korup biasa,
    karena split-nya sendiri belum sempat menghasilkan batch apa pun)."""


def split_by_channel(raw_data: bytes, filename: str) -> dict[str, bytes]:
    """Return {nama_channel_asli: csv_bytes_untuk_channel_itu}, urut sesuai
    kemunculan pertama tiap channel di file. Nama channel yang dipakai
    adalah kemunculan PERTAMA (mempertahankan huruf besar/kecil aslinya,
    misal 'Shopee' bukan 'shopee') supaya nama Source yang ke-buat rapi."""
    rows = read_rows(raw_data, filename)
    if not rows:
        ext = filename[filename.rfind(".") :].lower() if "." in filename else ""
        raise MixedChannelError(
            f"File kosong atau ekstensi '{ext}' tidak didukung (cuma .csv/.xlsx)."
        )

    header = rows[0]
    header_norm = [normalize_channel_value(h) for h in header]
    channel_col_idx = next(
        (i for i, h in enumerate(header_norm) if h in CHANNEL_COLUMN_ALIASES), None
    )
    if channel_col_idx is None:
        raise MixedChannelError(
            "Mode 'File ini campur beberapa channel' butuh kolom 'channel' "
            "(atau 'platform'/'marketplace'/'sumber') di file, tapi tidak "
            "ditemukan. Kalau file ini cuma dari 1 channel, pilih channel-nya "
            "langsung di dropdown, jangan pakai mode ini."
        )

    groups: dict[str, dict] = {}  # norm_key -> {"display_name": str, "rows": [...]}
    missing_rows = []
    for row_num, row in enumerate(rows[1:], start=2):
        value = row[channel_col_idx] if channel_col_idx < len(row) else None
        if value is None or str(value).strip() == "":
            missing_rows.append(row_num)
            continue
        display_name = str(value).strip()
        norm_key = normalize_channel_value(display_name)
        if norm_key not in groups:
            groups[norm_key] = {"display_name": display_name, "rows": []}
        groups[norm_key]["rows"].append(row)

    if missing_rows:
        examples = ", ".join(str(n) for n in missing_rows[:10])
        more = f" (+{len(missing_rows) - 10} baris lain)" if len(missing_rows) > 10 else ""
        raise MixedChannelError(
            f"{len(missing_rows)} baris tidak punya nilai kolom channel "
            f"(baris: {examples}{more}). Semua baris wajib punya nilai channel "
            f"di mode ini -- lengkapi dulu file-nya lalu upload ulang."
        )

    if not groups:
        raise MixedChannelError("Tidak ada baris data ditemukan setelah header.")

    return {g["display_name"]: _rows_to_csv(header, g["rows"]) for g in groups.values()}


def _rows_to_csv(header: list, rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")
