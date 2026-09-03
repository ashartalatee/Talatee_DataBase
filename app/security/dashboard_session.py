"""
Autentikasi sesi login untuk dashboard (manusia via browser), terpisah dari
app/security/api_key.py yang khusus machine-to-machine.

Cara pakai: cookie httpOnly `talatee_session`, di-set lewat POST /auth/login.
"""
from fastapi import Depends, HTTPException, Request
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_MAX_AGE = 60 * 60 * 12  # 12 jam

# ------------------------------------------------------------------
# TEMPORARY: login dimatikan sementara untuk pemakaian lokal-only.
# Set ke False lagi kalau mau aktifkan login sungguhan (wajib True
# sebelum deploy ke mana pun yang bukan localhost).
# ------------------------------------------------------------------
DISABLE_LOGIN_FOR_LOCAL_DEV = True


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret_key)


def verify_admin_credentials(username: str, password: str) -> bool:
    if username != settings.dashboard_admin_username:
        return False
    return pwd_context.verify(password, settings.dashboard_admin_password_hash)


def create_session_token(username: str) -> str:
    return _serializer().dumps({"username": username})


def require_dashboard_session(request: Request) -> str:
    """
    Dependency FastAPI — pasang di router dashboard lewat
    `APIRouter(dependencies=[Depends(require_dashboard_session)])`.
    Raise 401 kalau cookie sesi tidak ada/invalid/expired.
    """
    if DISABLE_LOGIN_FOR_LOCAL_DEV:
        return "admin"

    token = request.cookies.get("talatee_session")
    if not token:
        raise HTTPException(status_code=401, detail="Belum login.")
    try:
        data = _serializer().loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Sesi tidak valid atau kadaluarsa.")
    return data["username"]