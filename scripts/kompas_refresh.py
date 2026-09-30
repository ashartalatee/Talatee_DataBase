"""Ambil bacaan segar untuk Kompas dan isi 'Hari ini'.

Jalankan dari folder utama repo (venv aktif):
  python scripts/kompas_refresh.py              # ambil, simpan, isi hari ini
  python scripts/kompas_refresh.py --check      # tes semua sumber, tidak menyimpan apa pun
  python scripts/kompas_refresh.py --username NAMA_LOGIN
"""
import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.kompas_feed import FEEDS, collect_candidates, fill_today, refresh_candidates  # noqa: E402


def print_report(report):
    for name, status, total, good, err in report:
        if status == "ok":
            print(f"  [OK   ] {name}: {total} item, {good} lolos saring")
        else:
            print(f"  [GAGAL] {name}: {err}")
    ok = sum(1 for r in report if r[1] == "ok")
    print(f"  {ok} dari {len(report)} sumber bisa dibaca.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="tes sumber tanpa menyimpan")
    ap.add_argument("--username", help="nama login dashboard (otomatis dideteksi kalau hanya ada satu)")
    args = ap.parse_args()

    if args.check:
        print(f"Mengetes {len(FEEDS)} sumber...")
        cands, report = collect_candidates(datetime.now(timezone.utc))
        print_report(report)
        print(f"\nTotal {len(cands)} kandidat lolos saring. Contoh teratas:")
        for c in sorted(cands, key=lambda c: -c["score"])[:8]:
            print(f"  - [{c['score']:>3}] {c['title'][:90]}  ({c['source_name']})")
        return

    from app.db.session import get_db
    from app.models.kompas_checkin import KompasCheckin

    gen = get_db()
    db = next(gen)
    try:
        username = args.username
        if not username:
            names = [n for (n,) in db.query(KompasCheckin.username).distinct().all()]
            if len(names) != 1:
                sys.exit("Tidak bisa menebak nama login. Jalankan dengan: --username NAMA_LOGIN")
            username = names[0]

        today = date.today()
        added, report = refresh_candidates(db, username, today)
        filled = fill_today(db, username, today)
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] pengguna={username}")
        print_report(report)
        print(f"Kandidat baru: {added}. Ditambahkan ke Hari ini: {filled}.")
    finally:
        gen.close()


if __name__ == "__main__":
    main()
