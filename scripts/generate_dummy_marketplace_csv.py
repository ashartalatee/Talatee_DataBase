"""
Generate 4 file CSV dummy transaksi marketplace skincare (Shopee, Lazada,
TikTokShop, WhatsApp) untuk SATU tanggal -- TIDAK upload otomatis. File-nya
disimpan lokal, kamu upload sendiri manual lewat dashboard (tombol
"Upload Data") supaya benar-benar ngerasain alur upload -> Process Data ->
Quality -> Analytics-nya, bukan cuma lihat angka numpuk.

Kenapa generate-nya tetap otomatis (bukan diketik manual satu-satu): ngetik
15-40 baris data dummy per channel per hari itu kerja berulang yang tidak
ada nilai belajarnya -- yang penting buat dipahami adalah ALUR SISTEMNYA
(upload -> proses -> quality -> insight), bukan isi datanya sendiri.

CARA PAKAI:
    python scripts/generate_dummy_marketplace_csv.py                  # hari ini, 4 file
    python scripts/generate_dummy_marketplace_csv.py --date 2026-09-01
    python scripts/generate_dummy_marketplace_csv.py --rows 20-50
    python scripts/generate_dummy_marketplace_csv.py --no-messy        # matikan anomali sengaja
    python scripts/generate_dummy_marketplace_csv.py --messy-rate 1.0  # paksa selalu ada anomali

File jadi di: dummy_data_archive/<channel>/<tanggal>.csv

SETELAH FILE JADI, upload manual lewat dashboard -- Business/Source/Dataset
name WAJIB persis ini tiap kali (case-sensitive, lihat catatan di
app/ingestion/engine.py):
    Business Name     : Dummy Skincare Marketplace
    Business Category : marketplace
    Source Name        : nama channel-nya (Shopee / Lazada / TikTokShop / WhatsApp)
    Dataset Name        : Transaksi Harian
"""
import argparse
import csv
import io
import random
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "dummy_data_archive"

CHANNELS = {
    "Shopee": "SP",
    "Lazada": "LZ",
    "TikTokShop": "TT",
    "WhatsApp": "WA",
}

# (nama produk, kategori, kisaran harga_satuan)
PRODUCTS = [
    ("Serum Vitamin C 20ml", "skincare-wajah", (65000, 150000)),
    ("Serum Niacinamide 10%", "skincare-wajah", (55000, 120000)),
    ("Toner Centella Asiatica", "skincare-wajah", (45000, 95000)),
    ("Sunscreen SPF50 PA++++", "skincare-wajah", (60000, 130000)),
    ("Moisturizer Ceramide", "skincare-wajah", (70000, 160000)),
    ("Facial Wash Salicylic Acid", "skincare-wajah", (35000, 75000)),
    ("Micellar Water 500ml", "skincare-wajah", (40000, 85000)),
    ("Sheet Mask Collagen (isi 5)", "skincare-wajah", (30000, 60000)),
    ("Body Lotion Glutathione", "skincare-tubuh", (45000, 90000)),
    ("Body Scrub Coffee", "skincare-tubuh", (50000, 100000)),
    ("Body Wash Whitening", "skincare-tubuh", (35000, 70000)),
    ("Hand Cream Shea Butter", "skincare-tubuh", (25000, 55000)),
    ("Lip Tint Matte", "makeup", (35000, 80000)),
    ("Cushion Foundation", "makeup", (90000, 220000)),
    ("Eyebrow Pencil Waterproof", "makeup", (30000, 65000)),
    ("Kolagen Drink Sachet (isi 10)", "suplemen-kecantikan", (80000, 180000)),
    ("Vitamin Kulit Kapsul (isi 30)", "suplemen-kecantikan", (95000, 250000)),
]

# Status yang DIKENALI sistem sebagai revenue: completed/success/sukses/
# berhasil/paid/lunas (lihat app/models/core_transaction.py REVENUE_STATUSES).
STATUS_WEIGHTS = [
    ("Completed", 75),
    ("Pending", 10),
    ("Cancelled", 10),
    ("Lunas", 5),
]

ANOMALY_RATE = 0.25


def _weighted_status() -> str:
    statuses, weights = zip(*STATUS_WEIGHTS)
    return random.choices(statuses, weights=weights, k=1)[0]


def _build_rows(channel: str, prefix: str, for_date: date, n_rows: int) -> list[dict]:
    rows = []
    for i in range(1, n_rows + 1):
        product, category, price_range = random.choice(PRODUCTS)
        qty = random.randint(1, 3)
        harga_satuan = random.randrange(price_range[0], price_range[1], 1000)
        rows.append({
            "order_id": f"{prefix}-{for_date:%Y%m%d}-{i:03d}",
            "tanggal": for_date.isoformat(),
            "channel": channel,
            "produk": product,
            "kategori": category,
            "qty": qty,
            "harga_satuan": harga_satuan,
            "subtotal": qty * harga_satuan,
            "status": _weighted_status(),
        })
    return rows


def _inject_duplicate_order_id(rows: list[dict]) -> str:
    i, j = random.sample(range(len(rows)), 2)
    rows[j]["order_id"] = rows[i]["order_id"]
    return "duplicate_order_id"


def _inject_subtotal_mismatch(rows: list[dict]) -> str:
    row = random.choice(rows)
    row["subtotal"] = row["subtotal"] + random.choice([-15000, 15000, 20000])
    return "subtotal_mismatch"


def _inject_unrecognized_status(rows: list[dict]) -> str:
    row = random.choice(rows)
    row["status"] = random.choice(["Diproses", "Dikirim", "On Delivery", "Menunggu Konfirmasi"])
    return "unrecognized_status"


def _inject_missing_subtotal(rows: list[dict]) -> str:
    row = random.choice(rows)
    row["subtotal"] = ""
    return "missing_subtotal"


ANOMALY_INJECTORS = [
    _inject_duplicate_order_id,
    _inject_subtotal_mismatch,
    _inject_unrecognized_status,
    _inject_missing_subtotal,
]

FIELDS = ["order_id", "tanggal", "channel", "produk", "kategori", "qty", "harga_satuan", "subtotal", "status"]


def rows_to_csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=str, default=None, help="Tanggal YYYY-MM-DD (default: hari ini)")
    parser.add_argument("--rows", type=str, default="15-40", help="Kisaran jumlah baris per channel")
    parser.add_argument("--no-messy", action="store_true", help="Matikan anomali sengaja")
    parser.add_argument("--messy-rate", type=float, default=ANOMALY_RATE, help="Peluang 0.0-1.0 ada anomali hari ini")
    args = parser.parse_args()

    for_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    lo, hi = (int(x) for x in args.rows.split("-"))

    messy_today = (not args.no_messy) and random.random() < args.messy_rate
    messy_channel = random.choice(list(CHANNELS)) if messy_today else None

    print(f"Generate file dummy untuk {for_date.isoformat()} ...\n")

    for channel, prefix in CHANNELS.items():
        n_rows = random.randint(lo, hi)
        rows = _build_rows(channel, prefix, for_date, n_rows)

        tag = ""
        if channel == messy_channel:
            random.choice(ANOMALY_INJECTORS)(rows)
            tag = "  <- ada 1 baris 'aneh' sengaja di sini, coba temukan sendiri"

        channel_dir = ARCHIVE_DIR / channel
        channel_dir.mkdir(parents=True, exist_ok=True)
        path = channel_dir / f"{channel.lower()}_{for_date.isoformat()}.csv"
        path.write_bytes(rows_to_csv(rows))

        print(f"  [{channel:10s}] {n_rows:3d} baris -> {path.relative_to(ROOT)}{tag}")

    print("\nSelesai generate. Sekarang buka dashboard -> Upload Data, upload ke-4 file")
    print("di atas SATU-SATU secara manual, dengan:")
    print("  Business Name     : Dummy Skincare Marketplace")
    print("  Business Category : marketplace")
    print("  Source Name        : nama channel-nya (sesuai nama folder di atas)")
    print("  Dataset Name        : Transaksi Harian")


if __name__ == "__main__":
    main()
