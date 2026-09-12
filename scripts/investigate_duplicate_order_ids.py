"""
Skrip investigasi SATU KALI PAKAI — bukan bagian permanen dari engine.
Tujuannya cuma untuk lihat: order_id yang sama itu muncul di batch/file
APA SAJA, supaya bisa diputuskan apakah tumpang tindihnya memang disengaja
(upload ulang/revisi) atau ini bug di sumber data.

Cara pakai (dari root folder project, venv aktif):
    python scripts/investigate_duplicate_order_ids.py <dataset_id>

Contoh:
    python scripts/investigate_duplicate_order_ids.py d9036bae-1bc9-43f6-8b41-88faf0654ac3
"""
import sys
from collections import defaultdict
from pathlib import Path

# Supaya "app" bisa di-import terlepas dari cara skrip ini dijalankan
# (python scripts/x.py menaruh folder scripts/ di sys.path, BUKAN root
# project — jadi kita tambahkan root project secara eksplisit).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models import CoreTransaction, Batch, File


def main(dataset_id: str):
    db = SessionLocal()
    try:
        rows = (
            db.query(
                CoreTransaction.order_id,
                CoreTransaction.batch_id,
                CoreTransaction.transaction_date,
                CoreTransaction.subtotal,
                CoreTransaction.status_raw,
                Batch.started_at,
                File.filename,
            )
            .join(Batch, Batch.id == CoreTransaction.batch_id)
            .outerjoin(File, File.batch_id == Batch.id)
            .filter(CoreTransaction.dataset_id == dataset_id)
            .filter(CoreTransaction.order_id.isnot(None))
            .order_by(CoreTransaction.order_id, Batch.started_at)
            .all()
        )

        by_order_id = defaultdict(list)
        for r in rows:
            by_order_id[r.order_id].append(r)

        duplicates = {oid: rs for oid, rs in by_order_id.items() if len(rs) > 1}

        if not duplicates:
            print("Tidak ada order_id duplikat ditemukan.")
            return

        print(f"Ditemukan {len(duplicates)} order_id yang duplikat "
              f"({sum(len(rs) for rs in duplicates.values())} baris total).\n")

        # Ringkasan: apakah duplikat SELALU antar-batch berbeda (indikasi
        # upload ulang) atau ADA yang dalam 1 batch yang sama (indikasi lain)?
        cross_batch = 0
        same_batch = 0
        batch_pair_counter = defaultdict(int)
        for oid, rs in duplicates.items():
            batch_ids = {r.batch_id for r in rs}
            if len(batch_ids) > 1:
                cross_batch += 1
                filenames = tuple(sorted({r.filename or "?" for r in rs}))
                batch_pair_counter[filenames] += 1
            else:
                same_batch += 1

        print(f"- Duplikat ANTAR batch berbeda : {cross_batch} order_id")
        print(f"- Duplikat DALAM 1 batch yang sama : {same_batch} order_id\n")

        if batch_pair_counter:
            print("Kombinasi file yang paling sering tumpang tindih:")
            for filenames, count in sorted(batch_pair_counter.items(), key=lambda x: -x[1])[:10]:
                print(f"  {count:>3}x  {' <-> '.join(filenames)}")
            print()

        print("Contoh 10 order_id duplikat pertama (order_id | file | tanggal | subtotal | status):")
        for oid, rs in list(duplicates.items())[:10]:
            print(f"\n  order_id = {oid}")
            for r in rs:
                print(f"    {r.filename or '?':30}  {r.transaction_date}  {r.subtotal}  {r.status_raw}")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Pakai: python scripts/investigate_duplicate_order_ids.py <dataset_id>")
        sys.exit(1)
    main(sys.argv[1])
