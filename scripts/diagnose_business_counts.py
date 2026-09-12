"""
Skrip diagnosa SATU KALI PAKAI — untuk membuktikan kenapa dashboard
menunjukkan "0 sources" padahal scripts/cleanup_orphan_businesses.py bilang
business-nya PUNYA source (tidak yatim). Read-only, tidak mengubah apa pun.

Cara pakai (dari root project, venv aktif):
    python scripts/diagnose_business_counts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models import Business, Source


def main():
    db = SessionLocal()
    try:
        businesses = db.query(Business).order_by(Business.created_at).all()
        print(f"Total business di DB: {len(businesses)}\n")

        no_source_at_all = 0
        has_source_all_trashed = 0
        has_source_some_active = 0

        for b in businesses:
            sources = db.query(Source).filter(Source.business_id == b.id).all()
            if not sources:
                no_source_at_all += 1
                continue
            active = [s for s in sources if s.deleted_at is None]
            trashed = [s for s in sources if s.deleted_at is not None]
            if active:
                has_source_some_active += 1
            elif trashed:
                has_source_all_trashed += 1
                print(
                    f"  [SEMUA SOURCE DI-TRASH] {b.name!r:45s} -> "
                    f"{len(trashed)} source, semua deleted_at terisi. Contoh: "
                    f"{trashed[0].name!r} dihapus {trashed[0].deleted_at} oleh {trashed[0].deleted_by!r}"
                )

        print("\n--- Ringkasan ---")
        print(f"Tidak punya source sama sekali (yatim asli) : {no_source_at_all}")
        print(f"Punya source tapi SEMUA di-trash             : {has_source_all_trashed}")
        print(f"Punya minimal 1 source aktif                 : {has_source_some_active}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
