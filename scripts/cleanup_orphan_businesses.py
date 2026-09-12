"""
Skrip cleanup SATU KALI PAKAI — bukan bagian permanen dari engine.

Menghapus Business yang YATIM (0 source sama sekali). Ini AMAN dihapus
tanpa lewat alur Trash/Purge biasa (yang untuk Source/Dataset/Batch)
karena business tanpa source tidak punya anak apa pun yang bisa jadi
korban cascade -- tidak ada risiko kehilangan data nyata.

KENAPA INI BISA TERJADI: IngestionEngine.run() (app/ingestion/engine.py)
commit Business, Source, Connector, Dataset, Batch di 4 langkah TERPISAH
(bukan 1 transaksi). Kalau proses gagal setelah Business ke-commit tapi
sebelum Source dibuat, Business itu jadi yatim permanen. Ini paling sering
kejadian kalau test suite (pytest tests/test_reconciliation.py,
tests/test_data_passport.py, dst -- lihat nama business
"Reconciliation Business <suffix>" / "Passport Business <suffix>")
dijalankan ke database yang sama dengan yang dipakai dashboard sehari-hari,
bukan ke database test terpisah.

Cara pakai (dari root project, venv aktif):
    python scripts/cleanup_orphan_businesses.py            # dry-run, cuma tampilkan daftar
    python scripts/cleanup_orphan_businesses.py --execute   # betulan hapus

Business yang PUNYA minimal 1 source (walau source-nya sedang di-trash)
TIDAK PERNAH disentuh skrip ini -- untuk itu pakai halaman Sampah di
dashboard, bukan skrip ini.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func

from app.db.session import SessionLocal
from app.models import Business, Source


def main(execute: bool):
    db = SessionLocal()
    try:
        orphans = (
            db.query(Business)
            .outerjoin(Source, Source.business_id == Business.id)
            .group_by(Business.id)
            .having(func.count(Source.id) == 0)
            .order_by(Business.created_at)
            .all()
        )

        if not orphans:
            print("Tidak ada business yatim (0 source). Tidak ada yang perlu dibersihkan.")
            return

        print(f"Ditemukan {len(orphans)} business tanpa source sama sekali:\n")
        for b in orphans:
            print(f"  - {b.name!r:50s} ({b.category}, dibuat {b.created_at:%Y-%m-%d %H:%M})")

        if not execute:
            print(
                "\nIni baru DRY-RUN, belum ada yang dihapus. Cek daftar di atas dulu -- kalau "
                "ada nama yang kamu kenali sebagai business asli (bukan hasil test), JANGAN "
                "jalankan --execute sebelum itu diberi source dulu (upload data ke situ)."
            )
            print("Kalau daftar di atas sudah aman semua, jalankan ulang dengan:")
            print("    python scripts/cleanup_orphan_businesses.py --execute")
            return

        for b in orphans:
            db.delete(b)
        db.commit()
        print(f"\n{len(orphans)} business yatim sudah dihapus permanen.")
    finally:
        db.close()


if __name__ == "__main__":
    main(execute="--execute" in sys.argv)
