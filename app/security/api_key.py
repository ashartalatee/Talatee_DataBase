"""
Autentikasi machine-to-machine sederhana lewat API key, dipakai untuk
endpoint yang menerima data dari LUAR Talatee (produk lain seperti
buku-kas-warung). Bukan sistem login/session untuk dashboard.

Cara pakai: kirim header `Authorization: Bearer <key>`.
"""
import hashlib

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models import ApiKey


def hash_key(plaintext_key: str) -> str:
    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()


def require_api_key(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ApiKey:
    """
    Dependency FastAPI — pasang di route yang butuh proteksi API key, lewat
    `Depends(require_api_key)`. Raise 401 kalau header tidak ada/format salah/
    key tidak valid/key sudah di-revoke.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Header 'Authorization: Bearer <api_key>' wajib diisi.",
        )

    plaintext_key = authorization.removeprefix("Bearer ").strip()
    if not plaintext_key:
        raise HTTPException(status_code=401, detail="API key kosong.")

    key_hash = hash_key(plaintext_key)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()

    if api_key is None:
        raise HTTPException(status_code=401, detail="API key tidak valid.")
    if api_key.status != "active":
        raise HTTPException(status_code=401, detail="API key sudah tidak aktif (revoked).")

    api_key.last_used_at = func.now()
    db.commit()

    return api_key
