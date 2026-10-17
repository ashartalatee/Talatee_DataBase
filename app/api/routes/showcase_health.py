"""
Status kesehatan komponen untuk halaman Showcase (ruang kendali Panggung).

HANYA membaca: tidak menulis ke database, tidak membuat bucket, dan tidak
memanggil model Hermes (tidak ada biaya token). Tiap komponen dicek terpisah
dengan batas waktu pendek dan berjalan paralel, jadi satu komponen yang mati
tidak menunda atau menjatuhkan yang lain.

Arti status:
  ok            komponen merespons dengan wajar
  slow          merespons, tetapi lebih lambat dari SLOW_MS
  down          tidak terjangkau, timeout, atau menolak
  unconfigured  belum diatur di .env (bukan berarti rusak)

Catatan: untuk Hermes dan WhatsApp, "ok" berarti server di alamat itu
menjawab. Ini bukan bukti bahwa percakapan atau pengiriman pesan berhasil.

Pesan yang dikembalikan sengaja berupa kategori umum ("tidak terjangkau",
"timeout", ...) -- tidak pernah teks galat mentah, alamat internal, atau
kunci, karena panel ini bisa tampil di layar saat siaran langsung.
"""
import asyncio
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.storage import minio_client

router = APIRouter(
    prefix="/showcase",
    tags=["showcase"],
    dependencies=[Depends(require_dashboard_session)],
)

TIMEOUT_S = 3.0  # batas tunggu per komponen
SLOW_MS = 1000  # lebih lambat dari ini ditandai "slow"

# Status sesi WAHA yang aman ditampilkan apa adanya.
_WAHA_SHOWABLE = {"STOPPED", "STARTING", "SCAN_QR_CODE", "FAILED"}


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _row(cid: str, label: str, status: str, latency_ms=None, note: str = "") -> dict:
    return {"id": cid, "label": label, "status": status, "latency_ms": latency_ms, "note": note}


def _done(cid: str, label: str, started: float, note: str = "") -> dict:
    ms = _ms(started)
    if ms > SLOW_MS:
        return _row(cid, label, "slow", ms, "Merespons lambat")
    return _row(cid, label, "ok", ms, note)


def _fail(cid: str, label: str, started: float, note: str) -> dict:
    return _row(cid, label, "down", _ms(started), note)


async def _http_get(url: str, headers: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        return await client.get(url, headers=headers or {})


async def _check_postgres(db: Session) -> dict:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(
            asyncio.to_thread(lambda: db.execute(text("SELECT 1"))), TIMEOUT_S
        )
    except asyncio.TimeoutError:
        return _fail("postgres", "Postgres", started, "Tidak merespons dalam batas waktu")
    except Exception:
        return _fail("postgres", "Postgres", started, "Tidak bisa terhubung")
    return _done("postgres", "Postgres", started)


async def _check_minio() -> dict:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(asyncio.to_thread(minio_client.ping), TIMEOUT_S)
    except asyncio.TimeoutError:
        return _fail("minio", "Penyimpanan (MinIO)", started, "Tidak merespons dalam batas waktu")
    except Exception:
        return _fail("minio", "Penyimpanan (MinIO)", started, "Tidak bisa terhubung")
    return _done("minio", "Penyimpanan (MinIO)", started)


async def _check_hermes() -> dict:
    cid, label = "hermes", "Hermes"
    started = time.perf_counter()
    base = (settings.hermes_api_url or "").rstrip("/")
    if not base:
        return _row(cid, label, "unconfigured", None, "Alamat Hermes belum diisi")
    try:
        resp = await _http_get(f"{base}/health")
    except httpx.TimeoutException:
        return _fail(cid, label, started, "Tidak merespons dalam batas waktu")
    except httpx.HTTPError:
        return _fail(cid, label, started, "Tidak terjangkau (apakah API server Hermes aktif?)")
    # Respons apa pun (termasuk 404 untuk path ini) berarti prosesnya hidup.
    if resp.status_code >= 500:
        return _fail(cid, label, started, "Server membalas error")
    if not settings.hermes_api_key:
        return _row(cid, label, "unconfigured", _ms(started), "Terjangkau, tetapi API key belum diisi")
    return _done(cid, label, started, "Terjangkau")


async def _check_whatsapp() -> dict:
    cid, label = "whatsapp", "WhatsApp (WAHA)"
    started = time.perf_counter()
    base = (settings.waha_url or "").rstrip("/")
    if not base:
        return _row(cid, label, "unconfigured", None, "Alamat WAHA belum diisi (WAHA_URL di .env)")
    headers = {"X-Api-Key": settings.waha_api_key} if settings.waha_api_key else {}
    try:
        resp = await _http_get(f"{base}/api/sessions", headers)
    except httpx.TimeoutException:
        return _fail(cid, label, started, "Tidak merespons dalam batas waktu")
    except httpx.HTTPError:
        return _fail(cid, label, started, "Tidak terjangkau")
    if resp.status_code in (401, 403):
        return _fail(cid, label, started, "Kredensial ditolak")
    if resp.status_code != 200:
        return _fail(cid, label, started, "Server membalas error")
    try:
        sessions = resp.json()
    except ValueError:
        return _done(cid, label, started, "Terjangkau")
    statuses = (
        [s.get("status") for s in sessions if isinstance(s, dict)]
        if isinstance(sessions, list)
        else []
    )
    if "WORKING" in statuses:
        return _done(cid, label, started, "Sesi aktif")
    if not statuses:
        return _fail(cid, label, started, "Belum ada sesi berjalan")
    shown = next((s for s in statuses if s in _WAHA_SHOWABLE), None)
    return _fail(cid, label, started, f"Sesi tidak aktif ({shown})" if shown else "Sesi tidak aktif")


@router.get("/health")
async def showcase_health(db: Session = Depends(get_db)) -> dict:
    postgres, minio, whatsapp, hermes = await asyncio.gather(
        _check_postgres(db), _check_minio(), _check_whatsapp(), _check_hermes()
    )
    # Urutan mengikuti arah data: pesan masuk -> API -> penyimpanan -> Hermes.
    components = [
        _row("api", "API", "ok", None, "Merespons"),
        postgres,
        minio,
        whatsapp,
        hermes,
    ]
    statuses = {c["status"] for c in components}
    if "down" in statuses:
        overall = "down"
    elif "slow" in statuses:
        overall = "degraded"
    else:
        overall = "ok"
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "components": components,
    }
