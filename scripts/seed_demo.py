"""
Siapkan bisnis demo "Talatee Skincare" dan API key demo yang TERIKAT ke bisnis itu.

Jalankan dari root project dengan venv aktif:
    python scripts/seed_demo.py                        # buat bisnis + key bila belum ada
    python scripts/seed_demo.py --new-key              # cabut key demo lama, buat key baru
    python scripts/seed_demo.py --adopt "Warung Demo"  # tandai bisnis yang sudah ada sebagai demo

Aman dijalankan berulang. Key ASLI hanya ditampilkan SEKALI di terminal;
yang disimpan di database hanya hash-nya.
"""
import argparse
import secrets
import sys

sys.path.insert(0, ".")

from sqlalchemy.engine.url import make_url  # noqa: E402

from app.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import ApiKey, Business  # noqa: E402
from app.security.api_key import hash_key  # noqa: E402

DEMO_BUSINESS_NAME = "Talatee Skincare"
DEMO_BUSINESS_CATEGORY = "marketplace"
DEMO_KEY_NAME = "Panggung Demo"


def ensure_demo_business(db, name=DEMO_BUSINESS_NAME):
    """Kembalikan (bisnis, dibuat_baru). Menolak bila nama dipakai bisnis non-demo."""
    matches = db.query(Business).filter(Business.name == name).all()
    if len(matches) > 1:
        raise RuntimeError(f"Ada {len(matches)} bisnis bernama '{name}'. Bereskan dulu secara manual.")
    if matches:
        business = matches[0]
        if business.deleted_at is not None:
            raise RuntimeError(f"Bisnis '{name}' ada di Sampah. Pulihkan atau hapus permanen dulu.")
        if not business.is_demo:
            raise RuntimeError(
                f"Bisnis '{name}' sudah ada tetapi BUKAN bisnis demo. "
                "Seed berhenti supaya data nyata tidak tercampur."
            )
        return business, False
    business = Business(name=name, category=DEMO_BUSINESS_CATEGORY, status="active", is_demo=True)
    db.add(business)
    db.commit()
    db.refresh(business)
    return business, True


def ensure_demo_key(db, business, rotate=False):
    """Kembalikan key baru (plaintext), atau None bila key aktif sudah ada dan rotate=False."""
    active = (
        db.query(ApiKey)
        .filter(ApiKey.business_id == business.id, ApiKey.status == "active")
        .all()
    )
    if active and not rotate:
        return None
    for old in active:
        old.status = "revoked"
    plaintext = f"tal_{secrets.token_urlsafe(32)}"
    db.add(
        ApiKey(
            name=DEMO_KEY_NAME,
            key_hash=hash_key(plaintext),
            key_prefix=plaintext[:12],
            status="active",
            business_id=business.id,
        )
    )
    db.commit()
    return plaintext


def adopt_business(db, name, confirm):
    """Tandai bisnis yang sudah ada sebagai demo. `confirm(bisnis)` harus mengembalikan True."""
    matches = db.query(Business).filter(Business.name == name, Business.deleted_at.is_(None)).all()
    if not matches:
        raise RuntimeError(f"Bisnis '{name}' tidak ditemukan.")
    if len(matches) > 1:
        raise RuntimeError(f"Ada {len(matches)} bisnis aktif bernama '{name}'. Bereskan dulu.")
    business = matches[0]
    if business.is_demo:
        return business, False
    if not confirm(business):
        return business, False
    business.is_demo = True
    db.commit()
    return business, True


def _describe_target():
    url = make_url(settings.database_url)
    return f"{url.host}:{url.port}/{url.database}"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seed bisnis demo Talatee Skincare")
    ap.add_argument("--new-key", action="store_true", help="cabut key demo lama dan buat yang baru")
    ap.add_argument("--adopt", metavar="NAMA", help="tandai bisnis yang sudah ada sebagai demo")
    ap.add_argument("--yes", action="store_true", help="lewati pertanyaan konfirmasi database")
    args = ap.parse_args(argv)

    print(f"Database tujuan: {_describe_target()}")
    if not args.yes and input("Lanjut ke database ini? (y/N): ").strip().lower() != "y":
        print("Dibatalkan.")
        return 1

    db = SessionLocal()
    try:
        if args.adopt:
            def confirm(b):
                print(f"Akan menandai sebagai DEMO: '{b.name}' (id {b.id}, kategori {b.category}, {len(b.sources)} source)")
                return input("Ketik YA untuk melanjutkan: ").strip() == "YA"

            business, changed = adopt_business(db, args.adopt, confirm)
            print("Ditandai sebagai demo." if changed else "Tidak ada perubahan.")
            return 0

        business, created = ensure_demo_business(db)
        print(("Bisnis demo dibuat: " if created else "Bisnis demo sudah ada: ") + f"{business.name} (id {business.id})")
        key = ensure_demo_key(db, business, rotate=args.new_key)
        if key is None:
            print("API key demo aktif sudah ada (tidak ditampilkan ulang). Pakai --new-key untuk membuat yang baru.")
        else:
            print()
            print("=" * 70)
            print("API key demo (terikat ke bisnis demo). SALIN SEKARANG, tidak ditampilkan lagi:")
            print()
            print(f"  {key}")
            print()
            print("Simpan di .env sebagai DEMO_API_KEY=... (jangan di-commit).")
            print("=" * 70)
        return 0
    except RuntimeError as exc:
        print(f"BERHENTI: {exc}")
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())