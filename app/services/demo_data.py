"""
Pembuat data demo Panggung. Murni (tanpa database, tanpa jaringan), jadi mudah dites.

Menghasilkan CSV transaksi FIKTIF dengan kolom yang sama seperti scripts/demo_simulator.py,
sehingga lolos pipeline yang sama (parse -> Core -> validasi). Order id selalu unik
(awalan DEMO-) supaya pemeriksaan duplikat tidak gagal walau kendali ditekan berkali-kali.
Sebagian kecil pesanan dibatalkan: hanya status "completed" yang dihitung sebagai omzet.
"""
import csv
import io
import random
import uuid
from datetime import date, timedelta

COLUMNS = ["order_id", "tanggal", "produk", "kategori", "qty", "harga_satuan", "subtotal", "status"]

# (nama, kategori, harga satuan, bobot kemunculan)
CATALOG = [
    ("Serum Vitamin C", "Skincare", 89000, 5),
    ("Moisturizer Gel", "Skincare", 65000, 4),
    ("Sunscreen SPF50", "Skincare", 75000, 5),
    ("Lip Cream Matte", "Makeup", 55000, 4),
    ("Cushion Foundation", "Makeup", 129000, 2),
    ("Shampoo Anti Ketombe", "Perawatan Rambut", 48000, 3),
    ("Body Lotion", "Body Care", 42000, 4),
]
# (nama channel = nama source, porsi penjualan)
CHANNELS = [("TikTok Shop", 0.36), ("Shopee", 0.30), ("Lazada", 0.17), ("WhatsApp", 0.10), ("Website", 0.07)]
CHANNEL_NAMES = [c for c, _ in CHANNELS]

COMPLETED = "completed"
CANCELLED = "cancelled"
CANCEL_RATE = 0.08


def pick_channel(rng: random.Random) -> str:
    return rng.choices(CHANNEL_NAMES, weights=[s for _, s in CHANNELS])[0]


def _write_orders(rng, writer, day: date, n: int, tag: str, start: int):
    weights = [p[3] for p in CATALOG]
    revenue = completed = 0
    for i in range(n):
        name, category, price, _ = rng.choices(CATALOG, weights=weights)[0]
        qty = rng.choices([1, 2, 3], weights=[6, 3, 1])[0]
        status = CANCELLED if rng.random() < CANCEL_RATE else COMPLETED
        subtotal = price * qty
        if status == COMPLETED:
            revenue += subtotal
            completed += 1
        writer.writerow([f"DEMO-{tag}-{start + i:05d}", day.isoformat(), name, category, qty, price, subtotal, status])
    return revenue, completed


def make_batch_csv(rng: random.Random, n_orders: int, day: date | None = None):
    """Satu batch kecil (seperti satu kiriman kasir). Return (bytes, omzet, jumlah_pesanan_selesai)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(COLUMNS)
    revenue, completed = _write_orders(rng, writer, day or date.today(), n_orders, uuid.uuid4().hex[:8], 1)
    return buf.getvalue().encode("utf-8"), revenue, completed


def make_history_csv(rng: random.Random, share: float, days: int = 30, today: date | None = None, per_day_total: int = 60):
    """Riwayat `days` hari ke belakang untuk satu channel dengan porsi `share`; hari ini baru terisi sebagian."""
    today = today or date.today()
    tag = uuid.uuid4().hex[:8]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(COLUMNS)
    revenue = completed = counter = 0
    for i in range(days):
        day = today - timedelta(days=days - 1 - i)
        base = per_day_total * share * (0.8 + 0.4 * rng.random()) * (1 + 0.012 * i)
        if day == today:
            base *= 0.45
        n = max(1, round(base))
        r, c = _write_orders(rng, writer, day, n, tag, counter + 1)
        revenue += r
        completed += c
        counter += n
    return buf.getvalue().encode("utf-8"), revenue, completed
