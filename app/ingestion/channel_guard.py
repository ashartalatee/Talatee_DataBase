"""
Validasi opsional: kalau file yang di-upload punya kolom channel/platform,
SEMUA baris di dalamnya harus cocok dengan Source yang jadi tujuan upload.
Kalau tidak, upload ditolak (batch jadi "failed", bukan diam-diam masuk
sebagai data source yang salah) -- lihat percakapan 8 Sept 2026 soal risiko
data marketplace (Shopee/Lazada/dst) tercampur kalau file salah channel
ke-upload ke Source yang salah.

SENGAJA OPSIONAL: kalau file TIDAK punya kolom channel/platform sama sekali
(kasus paling umum -- data restoran/warung/klinik biasa tidak punya konsep
"channel"), fungsi ini tidak melakukan apa-apa. Jadi aman dipanggil untuk
SEMUA upload, bukan cuma yang marketplace.

Kalau file MEMANG campur beberapa channel sekaligus (satu file, banyak nilai
channel berbeda), itu BUKAN kasus untuk modul ini -- itu urusan mode
"File ini campur beberapa channel" di halaman upload, lihat
app/ingestion/mixed_channel.py yang men-split file itu jadi beberapa upload
terpisah SEBELUM sampai ke modul ini.

Dipanggil dari app/ingestion/engine.py, SEBELUM file disimpan ke MinIO --
kalau ValueError di-raise di sini, IngestionEngine menangkapnya dan
menandai batch "failed" dengan error_message ini (pola yang sama seperti
file korup/kosong), jadi tidak ada file/objek yang sempat ke-upload dulu
baru ketahuan salah.
"""
from app.ingestion.file_rows import CHANNEL_COLUMN_ALIASES, normalize_channel_value, read_rows


def check_channel_column(raw_data: bytes, filename: str, source_name: str) -> None:
    rows = read_rows(raw_data, filename)
    if not rows:
        return

    header = rows[0]
    header_norm = [normalize_channel_value(h) for h in header]
    channel_col_idx = next(
        (i for i, h in enumerate(header_norm) if h in CHANNEL_COLUMN_ALIASES), None
    )
    if channel_col_idx is None:
        return

    expected = normalize_channel_value(source_name)
    mismatches: list[tuple[int, str]] = []
    for row_num, row in enumerate(rows[1:], start=2):
        if channel_col_idx >= len(row):
            continue
        value = row[channel_col_idx]
        if value is None or str(value).strip() == "":
            continue
        if normalize_channel_value(value) != expected:
            mismatches.append((row_num, str(value)))

    if mismatches:
        examples = ", ".join(f"baris {n}: '{v}'" for n, v in mismatches[:5])
        more = f" (+{len(mismatches) - 5} baris lain)" if len(mismatches) > 5 else ""
        raise ValueError(
            f"File ini di-upload untuk source '{source_name}', tapi kolom "
            f"'{header[channel_col_idx]}' berisi nilai lain: {examples}{more}. "
            f"Upload dibatalkan supaya data tidak tercampur antar channel -- "
            f"cek lagi file-nya, atau upload ke source yang sesuai. Kalau file "
            f"ini MEMANG sengaja campur banyak channel, pakai opsi 'File ini "
            f"campur beberapa channel' di halaman upload."
        )
