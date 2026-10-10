"""
Simulator data demo untuk Showcase.

Mengirim batch transaksi FIKTIF ke endpoint upload mesin (POST /ingest/upload)
-- jalur yang sama dengan bridge Buku Kas Warung -- jadi seluruh pipeline
(penyimpanan mentah di MinIO, metadata di Postgres, status kepercayaan,
entri Eksperimen) benar-benar bekerja, bukan animasi.

Yang TIDAK dilakukan skrip ini: mengolah atau mempromosikan data. Batch masuk
sebagai data mentah berstatus INGESTED dan tampil di Eksperimen. Mengolah dan
menjadikannya TRUSTED tetap kamu lakukan sendiri di dashboard -- itu bagian
dari ceritanya, dan trust memang tidak pernah otomatis.

Pemakaian (dari folder root proyek, venv aktif, backend jalan):
    python scripts/demo_simulator.py --once
    python scripts/demo_simulator.py --interval 20 --max-batches 30

API key dibaca dari .env (DEMO_API_KEY, kalau tidak ada TALATEE_API_KEY) atau
dari environment. Sengaja TIDAK ada opsi --api-key di command line supaya
kunci tidak tersimpan di riwayat terminal, dan kunci tidak pernah dicetak.

Pengaman:
  - Nama business wajib mengandung "demo" -- mencegah data palsu masuk ke
    klien sungguhan karena salah ketik.
  - Alamat backend wajib localhost, kecuali diberi --allow-remote.
  - Jumlah batch dibatasi (--max-batches) supaya tidak membanjiri database.
"""
import argparse
import csv
import io
import os
import random
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

import httpx

try:
    from dotenv import dotenv_values
except ImportError:  # python-dotenv ikut terpasang bersama pydantic-settings
    dotenv_values = None

# (nama, kategori, harga satuan, bobot kemunculan)
# Produk dan kisaran harga dipilih supaya selaras dengan laporan WhatsApp demo.
PRODUCTS = [
    ("Snack Ringan", "Makanan", 8000, 5),
    ("Air Mineral", "Minuman", 5000, 4),
    ("Roti Bakar", "Makanan", 15000, 3),
    ("Es Kopi Kekinian", "Minuman", 18000, 3),
]

COLUMNS = ["order_id", "tanggal", "produk", "kategori", "qty", "harga_satuan", "subtotal", "status"]


def load_api_key():
    env = dotenv_values(".env") if dotenv_values else {}
    for name in ("DEMO_API_KEY", "TALATEE_API_KEY"):
        value = env.get(name) or os.environ.get(name)
        if value:
            return value
    return ""


def make_batch(rng, n_orders):
    """Satu baris per pesanan (satu produk, qty 1-3). Sebagian kecil dibatalkan
    supaya terlihat bahwa hanya status selesai yang dihitung sebagai omzet."""
    now = datetime.now()
    stamp = now.strftime("%Y%m%d%H%M%S")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(COLUMNS)
    revenue = 0
    weights = [p[3] for p in PRODUCTS]
    for i in range(1, n_orders + 1):
        name, category, price, _ = rng.choices(PRODUCTS, weights=weights)[0]
        qty = rng.choices([1, 2, 3], weights=[6, 3, 1])[0]
        status = "cancelled" if rng.random() < 0.08 else "completed"
        subtotal = price * qty
        if status == "completed":
            revenue += subtotal
        writer.writerow(
            [f"DEMO-{stamp}-{i:03d}", now.strftime("%Y-%m-%d"), name, category, qty, price, subtotal, status]
        )
    return buf.getvalue().encode("utf-8"), revenue


def main():
    p = argparse.ArgumentParser(description="Simulator data demo Showcase")
    p.add_argument("--url", default="http://localhost:8000", help="alamat backend")
    p.add_argument("--business", default="Warung Demo")
    p.add_argument("--source", default="Kasir")
    p.add_argument("--dataset", default=None, help="default: 'Penjualan <tanggal hari ini>'")
    p.add_argument("--interval", type=float, default=20.0, help="detik antar batch (minimal 2)")
    p.add_argument("--orders", type=int, default=8, help="rata-rata pesanan per batch")
    p.add_argument("--max-batches", type=int, default=30)
    p.add_argument("--once", action="store_true", help="kirim satu batch lalu selesai")
    p.add_argument("--seed", type=int, default=None, help="isi supaya data bisa diulang persis sama")
    p.add_argument("--allow-remote", action="store_true", help="izinkan alamat selain localhost")
    args = p.parse_args()

    if "demo" not in args.business.lower():
        print('BATAL: nama business harus mengandung "demo" supaya tidak masuk ke klien sungguhan.')
        return 2
    host = urlparse(args.url).hostname
    if host not in ("localhost", "127.0.0.1") and not args.allow_remote:
        print("BATAL: alamat backend bukan localhost. Pakai --allow-remote kalau memang disengaja.")
        return 2
    key = load_api_key()
    if not key:
        print("BATAL: API key tidak ditemukan (DEMO_API_KEY atau TALATEE_API_KEY di .env / environment).")
        return 2

    interval = max(args.interval, 2.0)  # order_id memakai detik; hindari tabrakan
    dataset = args.dataset or f"Penjualan {datetime.now():%Y-%m-%d}"
    endpoint = args.url.rstrip("/") + "/ingest/upload"
    headers = {"Authorization": f"Bearer {key}"}
    rng = random.Random(args.seed)

    print(f"Kirim ke {endpoint}")
    print(f"Tujuan: {args.business} / {args.source} / {dataset}")
    print("Tekan Ctrl+C untuk berhenti.\n")

    sent = rows_total = revenue_total = 0
    consecutive_fail = 0
    try:
        with httpx.Client(timeout=30.0) as client:
            while True:
                n = rng.randint(max(3, args.orders - 3), args.orders + 3)
                content, revenue = make_batch(rng, n)
                filename = f"demo_{datetime.now():%Y%m%d_%H%M%S}.csv"
                stamp = datetime.now().strftime("%H:%M:%S")
                try:
                    resp = client.post(
                        endpoint,
                        headers=headers,
                        data={
                            "business_name": args.business,
                            "source_name": args.source,
                            "dataset_name": dataset,
                            "business_category": "warung",
                        },
                        files={"file": (filename, content, "text/csv")},
                    )
                except httpx.HTTPError:
                    consecutive_fail += 1
                    print(f"[{stamp}] gagal: backend tidak terjangkau ({consecutive_fail}/3)")
                    if consecutive_fail >= 3:
                        print("Berhenti: backend tidak menjawab tiga kali berturut-turut.")
                        return 1
                else:
                    if resp.status_code in (401, 403):
                        print("Berhenti: API key ditolak. Buat kunci khusus demo dengan scripts/create_api_key.py")
                        print("lalu isi sebagai DEMO_API_KEY di .env.")
                        return 1
                    if resp.status_code == 201:
                        consecutive_fail = 0
                        status = (resp.json() or {}).get("status", "?")
                        sent += 1
                        rows_total += n
                        revenue_total += revenue
                        print(f"[{stamp}] batch {sent}: {n} baris, omzet {revenue:,} (belum diolah), status={status}")
                    else:
                        consecutive_fail += 1
                        print(f"[{stamp}] gagal: HTTP {resp.status_code} {resp.text[:160]}")
                        if consecutive_fail >= 3:
                            print("Berhenti: tiga kegagalan berturut-turut.")
                            return 1
                if args.once or sent >= args.max_batches:
                    break
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nDihentikan.")

    print(f"\nSelesai: {sent} batch, {rows_total} baris, omzet simulasi {revenue_total:,}.")
    print("Buka Eksperimen di dashboard untuk melihat datanya. Omzet baru terhitung setelah diolah dan di-promote.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
