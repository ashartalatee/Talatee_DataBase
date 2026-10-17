"""Kirim hook jurnal suara yang sudah jatuh tempo (3 jam setelah disimpan).

Dijalankan Task Scheduler tiap 10 menit lewat journal_dispatch.bat (venv aktif).
  python scripts/journal_dispatch.py            # proses yang jatuh tempo
  python scripts/journal_dispatch.py --status   # lihat antrean, tidak mengirim apa pun
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.kompas_journal import KompasJournal  # noqa: E402
from app.services.journal_dispatch import run_due  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        if args.status:
            rows = db.query(KompasJournal).order_by(KompasJournal.created_at.desc()).limit(10).all()
            for j in rows:
                print(f"{j.created_at:%Y-%m-%d %H:%M} {j.status:<10} kirim={j.send_at:%H:%M} percobaan={j.attempts} {j.error or ''}")
            return
        results = run_due(db)
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] diproses={len(results)} {[(str(i)[:8], s) for i, s in results]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
