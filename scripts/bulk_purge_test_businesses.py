"""
Skrip cleanup SATU KALI PAKAI — hapus PERMANEN business hasil test suite
(pytest) yang kepalang ke database dev yang sama dengan dashboard.

Match by NAME PREFIX ke pola yang sudah dikonfirmasi berasal dari
tests/*.py (lihat percakapan 7 Sep 2026): "Reconciliation Business",
"Passport Business", "Passport Corr Business", "Dedup Test Business",
"Dedup SameBatch Business", "BizRules Business", "Correction Business",
"Reject Test", "E2E Test Business", "E2E Duplicate Business".

Ini langsung PURGE (hapus permanen, skip tahap trash) lewat
app.services.trash.purge_business -- cascade penuh ke semua source/
dataset/batch/file/core_transactions di bawahnya. TIDAK BISA DIBATALKAN.

Cara pakai (dari root project, venv aktif):
    python scripts/bulk_purge_test_businesses.py             # dry-run, tampilkan daftar
    python scripts/bulk_purge_test_businesses.py --execute    # betulan hapus permanen

Business yang TIDAK cocok pola manapun di bawah (misal business asli kamu:
Resto padang, madura, Warung Ibu Sari, skincare, Lalapan, talatee center)
TIDAK PERNAH disentuh skrip ini.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models import Business
from app.services.trash import purge_business

TEST_NAME_PREFIXES = [
    "Reconciliation Business",
    "Passport Corr Business",
    "Passport Business",
    "Dedup SameBatch Business",
    "Dedup Test Business",
    "BizRules Business",
    "Correction Business",
    "Reject Test",
    "E2E Test Business",
    "E2E Duplicate Business",
]


def main(execute: bool):
    db = SessionLocal()
    try:
        all_businesses = db.query(Business).order_by(Business.created_at).all()
        targets = [
            b for b in all_businesses
            if any(b.name.startswith(p) for p in TEST_NAME_PREFIXES)
        ]

        if not targets:
            print("Tidak ada business yang cocok pola nama test. Tidak ada yang perlu dihapus.")
            return

        print(f"Ditemukan {len(targets)} business yang cocok pola nama test suite:\n")
        for b in targets:
            print(f"  - {b.name}")

        if not execute:
            print(
                f"\nIni baru DRY-RUN, belum ada yang dihapus. Kalau daftar di atas sudah "
                f"benar (tidak ada business asli kamu ikut ke-list), jalankan:\n"
                f"    python scripts/bulk_purge_test_businesses.py --execute"
            )
            return

        for b in targets:
            purge_business(db, b, deleted_by="cleanup-script", reason="bulk cleanup test suite artifacts")
        print(f"\n{len(targets)} business (beserta seluruh source/dataset/batch di bawahnya) sudah dihapus permanen.")
    finally:
        db.close()


if __name__ == "__main__":
    main(execute="--execute" in sys.argv)
