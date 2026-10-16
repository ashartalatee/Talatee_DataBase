"""Membuat file CSV demo untuk diseret ke Panggung saat live, dengan generator yang sama seperti Simulator data.

    python scripts/make_demo_csv.py                          # 3 file di folder demo_csv/
    python scripts/make_demo_csv.py --files 5 --orders 10-20 --out demo_csv

Isi dan tanggal berasal dari app/services/demo_data.py. Periksa "contoh baris" yang dicetak untuk
memastikan tanggalnya terbaru. Skrip ini tidak mengunggah apa pun: file diseret sendiri ke Panggung.
"""
import argparse
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import demo_data  # noqa: E402


def _span(text: str) -> tuple[int, int]:
    a, _, b = text.partition("-")
    lo = max(1, int(a))
    hi = max(lo, int(b or a))
    return lo, hi


def main() -> int:
    p = argparse.ArgumentParser(description="Buat CSV demo untuk Panggung")
    p.add_argument("--files", type=int, default=3, help="jumlah file (bawaan 3)")
    p.add_argument("--orders", default="8-14", help="jumlah pesanan per file, mis. 10-20 (bawaan 8-14)")
    p.add_argument("--out", default="demo_csv", help="folder tujuan (bawaan demo_csv)")
    a = p.parse_args()
    lo, hi = _span(a.orders)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for i in range(max(1, a.files)):
        data, revenue, _completed = demo_data.make_batch_csv(rng, rng.randint(lo, hi))
        name = f"penjualan_demo_{stamp}_{i + 1:02d}.csv"
        (out / name).write_bytes(data)
        lines = data.decode("utf-8", "replace").splitlines()
        rupiah = f"{int(revenue):,}".replace(",", ".")
        print(f"{name}: {max(0, len(lines) - 1)} baris, omzet selesai sekitar Rp {rupiah}")
        if len(lines) > 1:
            print("   contoh baris:", lines[1][:110])
    print(f"Selesai. Seret file dari folder '{out}' ke jendela Panggung.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
