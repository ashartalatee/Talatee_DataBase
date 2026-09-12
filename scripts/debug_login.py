"""
Skrip diagnostik SATU KALI PAKAI untuk debug "Username atau password salah"
di halaman login dashboard. Aman dijalankan -- tidak mengubah apa pun,
cuma membaca & menampilkan info (password_hash aman ditampilkan sebagian,
bukan reversible).

Cara pakai (dari root project, venv aktif):
    python scripts/debug_login.py
Lalu ikuti instruksi yang muncul di layar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.security.dashboard_session import verify_admin_credentials, DISABLE_LOGIN_FOR_LOCAL_DEV


def main():
    print("=== 1. Apa yang terbaca dari .env ===")
    print(f"DISABLE_LOGIN_FOR_LOCAL_DEV = {DISABLE_LOGIN_FOR_LOCAL_DEV}")
    print(f"dashboard_admin_username    = {settings.dashboard_admin_username!r}")

    h = settings.dashboard_admin_password_hash
    if not h:
        print("dashboard_admin_password_hash = KOSONG! .env tidak kebaca atau field ini belum diisi.")
        print("\n>>> PENYEBAB KETEMU: password_hash kosong. Cek lagi isi .env, pastikan baris")
        print(">>> DASHBOARD_ADMIN_PASSWORD_HASH=... ada isinya dan .env ada di folder yang benar.")
        return

    print(f"dashboard_admin_password_hash = {h[:15]}...{h[-6:]} (panjang: {len(h)} karakter)")
    if not h.startswith("$2b$") and not h.startswith("$2a$"):
        print("\n>>> PENYEBAB KETEMU: hash ini TIDAK diawali $2b$ atau $2a$ -- berarti bukan")
        print(">>> bcrypt hash yang valid. Kemungkinan pas copy-paste ke .env ada yang")
        print(">>> ke-potong atau ke-tambah karakter aneh. Generate ulang hash-nya.")
        return

    print("\n=== 2. Cek DISABLE_LOGIN_FOR_LOCAL_DEV ===")
    if DISABLE_LOGIN_FOR_LOCAL_DEV:
        print(">>> PENYEBAB KETEMU: DISABLE_LOGIN_FOR_LOCAL_DEV masih True di")
        print(">>> app/security/dashboard_session.py -- tapi ini seharusnya sudah")
        print(">>> tidak relevan untuk error 'salah', karena kalau True harusnya")
        print(">>> malah auto-login tanpa perlu form sama sekali.")

    print("\n=== 3. Test password ===")
    print("Ketik ulang PERSIS password yang Anda pakai waktu generate hash tadi.")
    print("(Ini cuma dicek di komputer Anda sendiri, tidak dikirim ke mana pun)")
    username = input(f"Username [{settings.dashboard_admin_username}]: ").strip() or settings.dashboard_admin_username
    import getpass
    password = getpass.getpass("Password: ")

    ok = verify_admin_credentials(username, password)
    print(f"\nHasil verify_admin_credentials: {'BERHASIL' if ok else 'GAGAL'}")

    if not ok:
        if username != settings.dashboard_admin_username:
            print(f">>> Username tidak cocok. Di .env: {settings.dashboard_admin_username!r}, yang Anda ketik: {username!r}")
        else:
            print(">>> Username cocok, tapi PASSWORD tidak cocok dengan hash di .env.")
            print(">>> Ini berarti password yang Anda ketik BEDA dari password yang dipakai")
            print(">>> waktu generate hash sebelumnya. Generate ulang hash-nya dengan")
            print(">>> password yang mau dipakai, lalu update .env lagi.")


if __name__ == "__main__":
    main()