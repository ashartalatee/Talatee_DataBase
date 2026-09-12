"""
Skrip arsip + pangkas untuk tabel deletion_logs (Riwayat Hapus Permanen).

Selalu MENGEKSPOR dulu (CSV) baris yang lebih tua dari batas umur yang
kamu tentukan, baru menghapusnya dari database -- dan HANYA menghapus
kalau ekspor filenya berhasil ditulis. Bukti tetap ada (di file), tabel
deletion_logs tetap ramping.

Cara pakai (dari root project, venv aktif):
    python scripts/archive_deletion_log.py                    # dry-run, cuma export, TIDAK hapus dari DB
    python scripts/archive_deletion_log.py --months 6         # ganti batas umur (default 6 bulan)
    python scripts/archive_deletion_log.py --execute          # export lalu betulan hapus dari DB

File hasil export ada di archives/deletion_logs/deletion_logs_archived_<tanggal>.csv
di root project -- simpan sendiri file itu (backup ke Google Drive/USB dsb,
sama seperti kamu simpan backup lain, lihat MASTER_GUIDE.md) karena begitu
baris ini dihapus dari DB, file CSV itu satu-satunya bukti yang tersisa.
"""
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models import DeletionLog

ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "archives" / "deletion_logs"

FIELDS = [
    "id", "level", "entity_id", "entity_name", "context_path",
    "batches_deleted", "files_deleted", "records_deleted",
    "reason", "deleted_by", "deleted_at",
]


def main(months: int, execute: bool):
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    db = SessionLocal()
    try:
        old_rows = (
            db.query(DeletionLog)
            .filter(DeletionLog.deleted_at < cutoff)
            .order_by(DeletionLog.deleted_at)
            .all()
        )

        if not old_rows:
            print(f"Tidak ada baris deletion_logs yang lebih tua dari {months} bulan. Tidak ada yang perlu diarsipkan.")
            return

        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        archive_path = ARCHIVE_DIR / f"deletion_logs_archived_{datetime.now():%Y-%m-%d_%H%M%S}.csv"

        with open(archive_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS)
            for row in old_rows:
                writer.writerow([getattr(row, field) for field in FIELDS])

        print(f"{len(old_rows)} baris (lebih tua dari {months} bulan, sebelum {cutoff:%Y-%m-%d}) diekspor ke:")
        print(f"  {archive_path}")

        if not execute:
            print(
                "\nIni baru DRY-RUN -- file di atas sudah ditulis (cek dulu isinya), tapi baris "
                "di tabel deletion_logs BELUM dihapus. Kalau file-nya sudah kamu cek dan aman, "
                "jalankan ulang dengan:\n"
                "    python scripts/archive_deletion_log.py --execute"
            )
            return

        ids = [row.id for row in old_rows]
        db.query(DeletionLog).filter(DeletionLog.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        print(f"\n{len(old_rows)} baris sudah dihapus dari tabel deletion_logs (aman -- sudah ada di file CSV di atas).")
    finally:
        db.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    months = 6
    if "--months" in args:
        months = int(args[args.index("--months") + 1])
    main(months=months, execute="--execute" in args)
