"""
Jalankan sekali untuk generate DASHBOARD_ADMIN_PASSWORD_HASH dan SESSION_SECRET_KEY,
lalu copy hasilnya ke file .env.

Cara pakai:
    python scripts/generate_dashboard_credentials.py
"""
import getpass
import secrets

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

password = getpass.getpass("Masukkan password admin dashboard yang mau dipakai: ")
password_hash = pwd_context.hash(password)
session_secret = secrets.token_hex(32)

print("\nCopy 3 baris ini ke .env kamu:\n")
print(f"DASHBOARD_ADMIN_USERNAME=admin")
print(f"DASHBOARD_ADMIN_PASSWORD_HASH={password_hash}")
print(f"SESSION_SECRET_KEY={session_secret}")
