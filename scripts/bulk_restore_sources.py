"""
Skrip pemulihan massal SATU KALI PAKAI — untuk kejadian 7 Sep 2026 di mana
62 dari 63 source ke-trash berurutan (lihat diagnose_business_counts.py).
Ini TIDAK menyentuh data apa pun selain kolom deleted_at/deleted_by di
tabel sources -- sama seperti klik "Pulihkan" di halaman Sampah, cuma
dikerjakan untuk banyak source sekaligus.

Cara pakai (dari root project, venv aktif):
    python scripts/bulk_restore_sources.py                 # dry-run, tampilkan semua source yang di-trash
    python scripts/bulk_restore_sources.py --all            # pulihkan SEMUA source yang di-trash
    python scripts/bulk_restore_sources.py --business "warung" --business "madura"
                                                              # pulihkan cuma source di business yang
                                                              # namanya MENGANDUNG teks itu (case-insensitive,
                                                              # bisa diulang --business beberapa kali)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models import Business, Source
from app.services.trash import restore_source


def main(restore_all: bool, business_filters: list[str]):
    db = SessionLocal()
    try:
        rows = (
            db.query(Source, Business.name)
            .join(Business, Source.business_id == Business.id)
            .filter(Source.deleted_at.isnot(None))
            .order_by(Source.deleted_at)
            .all()
        )

        if not rows:
            print("Tidak ada source di Sampah. Tidak ada yang perlu dipulihkan.")
            return

        if business_filters:
            needles = [f.lower() for f in business_filters]
            targets = [
                (s, bname) for s, bname in rows if any(n in bname.lower() for n in needles)
            ]
        elif restore_all:
            targets = rows
        else:
            targets = []

        print(f"Total source di Sampah: {len(rows)}")
        for s, bname in rows:
            mark = "-> DIPULIHKAN" if (s, bname) in targets else ""
            print(f"  [{bname}] {s.name}  (di-trash {s.deleted_at}) {mark}")

        if not targets:
            print(
                "\nIni baru DRY-RUN, belum ada yang dipulihkan. Jalankan ulang dengan --all "
                "(pulihkan semua) atau --business \"<nama>\" (pulihkan sebagian saja)."
            )
            return

        for s, _ in targets:
            restore_source(db, s)
        print(f"\n{len(targets)} source berhasil dipulihkan.")
    finally:
        db.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    restore_all = "--all" in args
    business_filters = []
    i = 0
    while i < len(args):
        if args[i] == "--business" and i + 1 < len(args):
            business_filters.append(args[i + 1])
            i += 2
        else:
            i += 1
    main(restore_all, business_filters)
