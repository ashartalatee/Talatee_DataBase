"""
Generate API key baru untuk integrasi produk (buku-kas-warung, dll).

Jalankan dari root project:
    python scripts/create_api_key.py "Buku Kas Warung"

Key ASLI (plaintext) cuma ditampilkan SEKALI di terminal setelah dibuat —
salin sekarang juga, tidak akan bisa ditampilkan lagi setelah ini (yang
disimpan di database cuma hash-nya, sesuai prinsip keamanan API key).
"""
import secrets
import sys

sys.path.insert(0, ".")  # supaya `import app...` ketemu saat dijalankan dari root

from app.db.session import SessionLocal  # noqa: E402
from app.models import ApiKey  # noqa: E402
from app.security.api_key import hash_key  # noqa: E402


def create_api_key(name: str) -> None:
    plaintext_key = f"tal_{secrets.token_urlsafe(32)}"
    key_prefix = plaintext_key[:12]  # buat identifikasi di UI/log tanpa expose full key

    db = SessionLocal()
    try:
        api_key = ApiKey(
            name=name,
            key_hash=hash_key(plaintext_key),
            key_prefix=key_prefix,
            status="active",
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
    finally:
        db.close()

    print()
    print("=" * 70)
    print(f"API key baru untuk '{name}' berhasil dibuat.")
    print()
    print(f"  {plaintext_key}")
    print()
    print("SALIN SEKARANG — key ini TIDAK akan ditampilkan lagi setelah ini.")
    print("Simpan di .env.local produk yang bersangkutan, misal:")
    print(f"  TALATEE_API_KEY={plaintext_key}")
    print("=" * 70)
    print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Cara pakai: python scripts/create_api_key.py \"Nama Integrasi\"")
        print("Contoh:     python scripts/create_api_key.py \"Buku Kas Warung\"")
        sys.exit(1)

    create_api_key(sys.argv[1])
