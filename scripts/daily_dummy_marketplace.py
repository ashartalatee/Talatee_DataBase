"""
Generate data dummy transaksi marketplace skincare (Shopee, Lazada,
TikTokShop, WhatsApp) untuk SATU tanggal, lalu langsung upload lewat
API publik (/ingest/upload, pakai API key) -- 4 file, 1 per channel,
semuanya masuk ke Business yang sama tapi Source berbeda per channel.

DIRANCANG SUPAYA TIDAK JADI KOTAK HITAM:
  1. Setiap file yang di-generate DISIMPAN DULU secara lokal (folder
     dummy_data_archive/<channel>/<tanggal>.csv) sebelum di-upload -- jadi
     kamu selalu bisa buka & baca file mentahnya kapan pun, tidak cuma
     percaya begitu saja ke hasil di dashboard.
  2. Sesekali (bukan tiap hari -- lihat ANOMALY_RATE), SATU baris di SATU
     channel sengaja dibikin "kotor": order_id bentrok, subtotal salah
     hitung, status yang tidak dikenali sistem, atau subtotal kosong.
     Ini persis kasus nyata yang bakal ditemui client asli kamu -- dan
     kesempatan buat kamu latihan pakai fitur Quality/Correction yang
     sudah kamu bangun sendiri. Skrip cuma kasih tahu CHANNEL & TANGGAL
     mana yang "dijebak" (bukan jenis anomalinya) -- coba temukan dulu
     lewat dashboard sebelum baca kode di bawah buat lihat jawabannya.

SETUP SEKALI SAJA sebelum dipakai:
    1. Buat API key khusus untuk script ini:
         python scripts/create_api_key.py "Dummy Marketplace Generator"
       Salin key yang muncul (cuma ditampilkan sekali).
    2. Set sebagai environment variable permanen (Windows):
         setx TALATEE_API_KEY "tal_xxxxxxxxxxxxx"
       Tutup & buka ulang terminal/Task Scheduler supaya env var kebaca.
    3. (opsional) Kalau backend TIDAK di localhost:8000, set juga:
         setx TALATEE_API_URL "http://100.126.173.20:8000"

CARA PAKAI:
    python scripts/daily_dummy_marketplace.py                    # hari ini
    python scripts/daily_dummy_marketplace.py --date 2026-09-01   # tanggal tertentu (backfill)
    python scripts/daily_dummy_marketplace.py --rows 20-50        # jumlah baris per channel (default 15-40)
    python scripts/daily_dummy_marketplace.py --no-messy          # matikan anomali (misal pas backfill banyak hari sekaligus)
    python scripts/daily_dummy_marketplace.py --messy-rate 1.0    # paksa selalu ada anomali (buat latihan langsung)

DIJADWALKAN OTOMATIS (Windows Task Scheduler):
    Program/script: <path venv>\\Scripts\\python.exe
    Arguments:       scripts\\daily_dummy_marketplace.py
    Start in:        <path root project>
    Trigger:          Daily, jam berapa pun (misal 23:55)

Business/Source/Dataset yang dipakai (SELALU nama ini, jangan diubah tanpa
sengaja -- lihat catatan di app/ingestion/engine.py: pencocokan nama
persis/case-sensitive, beda dikit = dianggap business/source baru):
    business_name     = "Dummy Skincare Marketplace"
    business_category = "marketplace"
    source_name        = nama channel (Shopee / Lazada / TikTokShop / WhatsApp)
    dataset_name        = "Transaksi Harian"
"""
import argparse
import csv
import io
import os
import random
import sys
from datetime import date, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "dummy_data_archive"

BUSINESS_NAME = "Dummy Skincare Marketplace"
BUSINESS_CATEGORY = "marketplace"
DATASET_NAME = "Transaksi Harian"

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
# "Pending"/"Cancelled" sengaja diikutkan supaya datanya realistis (tidak
# semua closing) tapi TIDAK dihitung sebagai revenue -- sesuai perilaku asli.
STATUS_WEIGHTS = [
    ("Completed", 75),
    ("Pending", 10),
    ("Cancelled", 10),
    ("Lunas", 5),
]

# Peluang PER HARI (bukan per channel) ada 1 anomali disisipkan ke SATU
# channel acak. 0.25 = kira-kira 1 dari 4 hari. Ganti lewat --messy-rate.
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
    """2 baris punya order_id sama dalam 1 file -- tes dedup 'okurensi
    terakhir menang' (lihat core_processor.py)."""
    i, j = random.sample(range(len(rows)), 2)
    rows[j]["order_id"] = rows[i]["order_id"]
    return "duplicate_order_id"


def _inject_subtotal_mismatch(rows: list[dict]) -> str:
    """subtotal TIDAK sama dengan qty x harga_satuan -- tes business rule
    validation (Quality tab harus nunjukin error)."""
    row = random.choice(rows)
    row["subtotal"] = row["subtotal"] + random.choice([-15000, 15000, 20000])
    return "subtotal_mismatch"


def _inject_unrecognized_status(rows: list[dict]) -> str:
    """status pakai istilah yang TIDAK ada di REVENUE_STATUSES -- transaksi
    ini tidak akan pernah dihitung revenue walau sebenarnya closing."""
    row = random.choice(rows)
    row["status"] = random.choice(["Diproses", "Dikirim", "On Delivery", "Menunggu Konfirmasi"])
    return "unrecognized_status"


def _inject_missing_subtotal(rows: list[dict]) -> str:
    """subtotal dikosongkan -- tes jalur 'kolom ada tapi nilainya kosong'
    (invalid_count di core_processor.py)."""
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


def archive_locally(channel: str, for_date: date, csv_bytes: bytes) -> Path:
    channel_dir = ARCHIVE_DIR / channel
    channel_dir.mkdir(parents=True, exist_ok=True)
    path = channel_dir / f"{channel.lower()}_{for_date.isoformat()}.csv"
    path.write_bytes(csv_bytes)
    return path


def upload_csv(client: httpx.Client, api_base: str, api_key: str, source_name: str, for_date: date, csv_bytes: bytes) -> dict:
    filename = f"{source_name.lower()}_{for_date:%Y-%m-%d}.csv"
    response = client.post(
        f"{api_base}/ingest/upload",
        headers={"Authorization": f"Bearer {api_key}"},
        data={
            "business_name": BUSINESS_NAME,
            "business_category": BUSINESS_CATEGORY,
            "source_name": source_name,
            "dataset_name": DATASET_NAME,
        },
        files={"file": (filename, csv_bytes, "text/csv")},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=str, default=None, help="Tanggal YYYY-MM-DD (default: hari ini)")
    parser.add_argument("--rows", type=str, default="15-40", help="Kisaran jumlah baris per channel, misal 15-40")
    parser.add_argument("--api-key", type=str, default=os.environ.get("TALATEE_API_KEY"))
    parser.add_argument("--api-url", type=str, default=os.environ.get("TALATEE_API_URL", "http://localhost:8000"))
    parser.add_argument("--no-messy", action="store_true", help="Matikan anomali sengaja (misal saat backfill banyak hari)")
    parser.add_argument("--messy-rate", type=float, default=ANOMALY_RATE, help="Peluang 0.0-1.0 ada anomali hari ini")
    args = parser.parse_args()

    if not args.api_key:
        print("TALATEE_API_KEY belum di-set. Jalankan dulu:")
        print('  python scripts/create_api_key.py "Dummy Marketplace Generator"')
        print('  setx TALATEE_API_KEY "tal_xxxxxxxxxxxxx"   (lalu buka terminal baru)')
        sys.exit(1)

    for_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    lo, hi = (int(x) for x in args.rows.split("-"))

    messy_today = (not args.no_messy) and random.random() < args.messy_rate
    messy_channel = random.choice(list(CHANNELS)) if messy_today else None

    print(f"Generate & upload data dummy untuk {for_date.isoformat()} ke {args.api_url} ...\n")

    with httpx.Client() as client:
        for channel, prefix in CHANNELS.items():
            n_rows = random.randint(lo, hi)
            rows = _build_rows(channel, prefix, for_date, n_rows)

            tag = ""
            if channel == messy_channel:
                random.choice(ANOMALY_INJECTORS)(rows)
                tag = "  <- ada 1 baris 'aneh' sengaja di sini, coba temukan di dashboard"

            csv_bytes = rows_to_csv(rows)
            archive_path = archive_locally(channel, for_date, csv_bytes)

            try:
                result = upload_csv(client, args.api_url, args.api_key, channel, for_date, csv_bytes)
                print(f"  [{channel:10s}] {n_rows:3d} baris -> batch {result['id']} ({result['status']}){tag}")
            except httpx.HTTPStatusError as exc:
                print(f"  [{channel:10s}] GAGAL: HTTP {exc.response.status_code} — {exc.response.text}")
            except httpx.ConnectError:
                print(f"  [{channel:10s}] GAGAL: tidak bisa connect ke {args.api_url} — backend jalan?")
                sys.exit(1)

            print(f"               (file lokal: {archive_path.relative_to(ROOT)})")

    print("\nSelesai. Cek dashboard -> Overview / Analytics untuk breakdown per channel,")
    print("dan Datasets -> [dataset] -> Quality kalau ada channel yang ditandai anomali di atas.")


if __name__ == "__main__":
    main()
