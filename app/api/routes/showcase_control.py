"""
Kendali demo untuk Panggung (laci "Kendali" di /stage). HANYA menyentuh bisnis demo.

Aturan yang dijaga di sini:
- Bisnis tujuan SELALU ditentukan server: satu-satunya bisnis berflag is_demo yang tidak di Sampah.
  Klien tidak pernah mengirim nama atau id bisnis. Kalau bukan tepat satu, aksi ditolak (409).
- Data masuk lewat _run_ingest (jalur upload yang sama dengan upload dashboard/mesin), lalu
  diolah, divalidasi, dan (opsional) di-promote lewat fungsi route yang SAMA dengan tombol di
  Eksperimen, jadi aturan trust tidak dilewati: batch yang tidak lolos validasi tetap NEEDS_REVIEW.
- Reset memakai trash_service (hapus sesaat lalu hapus permanen per source, tercatat di deletion_log)
  dan hanya untuk source milik bisnis demo. Perlu konfirmasi eksplisit di body.
- Dilindungi sesi dashboard. Pesan yang dikembalikan sengaja umum: tidak memuat teks galat mentah,
  alamat internal, atau kunci, karena laci ini bisa tampil saat siaran langsung.
"""
import asyncio
import io
import logging
import pathlib
import random
from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi import File as FastAPIFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes import core as core_routes
from app.api.routes.ingestion import _run_ingest
from app.db.session import get_db
from app.ingestion.core_processor import UnrecognizedSchemaError
from app.models import Batch, Business, CoreTransaction, Dataset, File as FileModel, Source
from app.security.dashboard_session import require_dashboard_session
from app.services import demo_data
from app.services import trash as trash_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/showcase",
    tags=["showcase-control"],
    dependencies=[Depends(require_dashboard_session)],
)

BUSINESS_CATEGORY = "marketplace"  # hanya dipakai kalau bisnis BARU dibuat; bisnis demo sudah ada
HISTORY_DATASET = "Histori 30 hari"
UPLOAD_SOURCE = "Upload manual"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_DEMO_BATCHES = 500
STEP_DELAY_S = 1.2  # jeda antar langkah supaya alurnya terlihat bergerak di Panggung

_busy = asyncio.Lock()  # backfill dan reset tidak boleh berjalan bersamaan


class TriggerBody(BaseModel):
    orders: int | None = None
    channel: str | None = None
    fast: bool = False  # tanpa jeda antar langkah (untuk tes)


class ResetBody(BaseModel):
    confirm: bool = False


class ControlResultOut(BaseModel):
    ok: bool
    message: str
    results: list[dict] = []


class ResetPreviewOut(BaseModel):
    sources: int
    datasets: int
    batches: int
    files: int
    transactions: int


# ----------------------------------------------------------------- pembantu

def _demo_business(db: Session) -> Business:
    rows = db.query(Business).filter(Business.is_demo.is_(True), Business.deleted_at.is_(None)).all()
    if not rows:
        raise HTTPException(status_code=409, detail="Bisnis demo belum ada. Jalankan scripts/seed_demo.py dulu.")
    if len(rows) > 1:
        raise HTTPException(status_code=409, detail="Ada lebih dari satu bisnis demo. Sisakan satu saja.")
    business = rows[0]
    # Engine mencari bisnis lewat NAMA; pastikan nama itu tidak ganda (termasuk di Sampah).
    if db.query(Business).filter(Business.name == business.name).count() != 1:
        raise HTTPException(status_code=409, detail="Nama bisnis demo dipakai lebih dari satu baris. Upload dihentikan.")
    return business


def _source_ids(db: Session, business: Business) -> list:
    return [sid for (sid,) in db.query(Source.id).filter(Source.business_id == business.id).all()]


def _count_batches(db: Session, business: Business) -> int:
    return (
        db.query(Batch.id)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .filter(Source.business_id == business.id)
        .count()
    )


def _guard_capacity(db: Session, business: Business) -> None:
    if _count_batches(db, business) >= MAX_DEMO_BATCHES:
        raise HTTPException(status_code=409, detail="Terlalu banyak batch demo. Reset demo dulu.")


async def _ingest_and_trust(db, business, *, source_name, dataset_name, filename, data, promote=True, delay=0.0) -> dict:
    """Upload -> olah -> validasi -> (opsional) promote, lewat jalur dan fungsi yang sama dengan dashboard."""
    upload = UploadFile(file=io.BytesIO(data), filename=filename)
    batch = await _run_ingest(business.name, source_name, dataset_name, upload, BUSINESS_CATEGORY, db)
    result = {
        "channel": source_name,
        "dataset": dataset_name,
        "rows": int(batch.records_saved or 0),
        "trust_status": "INGESTED",
        "ok": batch.status == "success",
    }
    if batch.status != "success":
        return result
    dataset_id = batch.dataset_id
    try:
        if delay:
            await asyncio.sleep(delay)
        core_routes.process_dataset_endpoint(dataset_id, db)
        quality = core_routes.get_dataset_quality(dataset_id, db)
        result["trust_status"] = quality["trust_status"]
        if delay:
            await asyncio.sleep(delay)
        if promote and quality["trust_status"] == "VALIDATING":
            core_routes.promote_dataset(dataset_id, db)
            result["trust_status"] = "TRUSTED"
    except UnrecognizedSchemaError:
        result["ok"] = False
        result["note"] = "format_tidak_dikenali"
    except Exception:  # noqa: BLE001 - detail hanya ke log server, bukan ke layar
        logger.exception("Pengolahan data demo gagal")
        result["ok"] = False
        result["note"] = "gagal_diolah"
    return result


# ------------------------------------------------------------------ endpoint

@router.post("/simulator/trigger", response_model=ControlResultOut)
async def trigger(body: TriggerBody | None = None, db: Session = Depends(get_db)):
    """Kirim satu batch demo (satu channel), lalu olah, validasi, dan promote."""
    body = body or TriggerBody()
    if body.channel is not None and body.channel not in demo_data.CHANNEL_NAMES:
        raise HTTPException(status_code=422, detail="Channel tidak dikenal.")
    business = _demo_business(db)
    _guard_capacity(db, business)

    rng = random.Random()
    channel = body.channel or demo_data.pick_channel(rng)
    n_orders = max(1, min(body.orders or rng.randint(6, 14), 60))
    data, _revenue, _completed = demo_data.make_batch_csv(rng, n_orders)
    result = await _ingest_and_trust(
        db, business,
        source_name=channel,
        dataset_name=f"Penjualan {date.today():%Y-%m-%d}",
        filename=f"demo_{datetime.now():%Y%m%d_%H%M%S}.csv",
        data=data,
        promote=True,
        delay=0.0 if body.fast else STEP_DELAY_S,
    )
    if result["ok"] and result["trust_status"] == "TRUSTED":
        message = f"{channel}: {n_orders} pesanan masuk dan terpercaya"
    elif result["ok"]:
        message = f"{channel}: {n_orders} pesanan masuk, status {result['trust_status']}"
    else:
        message = f"{channel}: batch masuk, tetapi tidak bisa diolah"
    return ControlResultOut(ok=result["ok"], message=message, results=[result])


@router.post("/demo/backfill", response_model=ControlResultOut)
async def backfill(db: Session = Depends(get_db)):
    """Isi riwayat 30 hari ke belakang untuk semua channel, supaya tren dan KPI langsung hidup."""
    if _busy.locked():
        raise HTTPException(status_code=409, detail="Aksi lain sedang berjalan.")
    async with _busy:
        business = _demo_business(db)
        exists = (
            db.query(Dataset.id)
            .join(Source, Dataset.source_id == Source.id)
            .filter(
                Source.business_id == business.id,
                Dataset.name == HISTORY_DATASET,
                Dataset.deleted_at.is_(None),
                Source.deleted_at.is_(None),
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="Data 30 hari sudah ada. Reset demo dulu kalau mau mengisi ulang.")
        _guard_capacity(db, business)

        rng = random.Random()
        results = []
        for channel, share in demo_data.CHANNELS:
            data, _r, _c = demo_data.make_history_csv(rng, share)
            results.append(
                await _ingest_and_trust(
                    db, business,
                    source_name=channel,
                    dataset_name=HISTORY_DATASET,
                    filename=f"histori_{channel.lower().replace(' ', '_')}.csv",
                    data=data,
                    promote=True,
                )
            )
    ok = all(r["ok"] for r in results)
    return ControlResultOut(
        ok=ok,
        message="Data 30 hari diisi" if ok else "Sebagian data 30 hari tidak bisa diolah",
        results=results,
    )


@router.post("/demo/upload", response_model=ControlResultOut)
async def upload(
    file: UploadFile = FastAPIFile(...),
    source_name: str = Form(UPLOAD_SOURCE),
    promote: bool = Form(True),
    db: Session = Depends(get_db),
):
    """Unggah file milikmu ke bisnis demo. Format kolom: lihat demo_data.COLUMNS."""
    filename = pathlib.PurePath(file.filename or "").name[:120]
    if not filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Hanya file .csv atau .xlsx.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File terlalu besar (maksimal 5 MB).")
    source = (source_name or "").strip()[:60] or UPLOAD_SOURCE

    business = _demo_business(db)
    _guard_capacity(db, business)
    result = await _ingest_and_trust(
        db, business,
        source_name=source,
        dataset_name=f"Upload {filename[:70]} {datetime.now():%H%M%S}",
        filename=filename,
        data=data,
        promote=promote,
        delay=STEP_DELAY_S,
    )
    if result.get("note") == "format_tidak_dikenali":
        message = f"File masuk, tetapi formatnya belum dikenali. Kolom yang dibutuhkan: {', '.join(demo_data.COLUMNS)}"
    elif result["ok"]:
        message = f"{filename}: {result['rows']} baris masuk, status {result['trust_status']}"
    else:
        message = f"{filename}: masuk, tetapi tidak bisa diolah"
    return ControlResultOut(ok=result["ok"], message=message, results=[result])


def _reset_counts(db: Session, business: Business) -> ResetPreviewOut:
    source_ids = _source_ids(db, business)
    if not source_ids:
        return ResetPreviewOut(sources=0, datasets=0, batches=0, files=0, transactions=0)
    dataset_ids = [i for (i,) in db.query(Dataset.id).filter(Dataset.source_id.in_(source_ids)).all()]
    batch_ids = [i for (i,) in db.query(Batch.id).filter(Batch.dataset_id.in_(dataset_ids)).all()] if dataset_ids else []
    files = db.query(FileModel.id).filter(FileModel.batch_id.in_(batch_ids)).count() if batch_ids else 0
    txs = db.query(CoreTransaction.id).filter(CoreTransaction.dataset_id.in_(dataset_ids)).count() if dataset_ids else 0
    return ResetPreviewOut(
        sources=len(source_ids), datasets=len(dataset_ids), batches=len(batch_ids), files=files, transactions=txs
    )


@router.get("/reset/preview", response_model=ResetPreviewOut)
def reset_preview(db: Session = Depends(get_db)):
    """Pratinjau jumlah yang akan dihapus. Tidak mengubah apa pun."""
    return _reset_counts(db, _demo_business(db))


@router.post("/reset", response_model=ControlResultOut)
async def reset_demo(
    body: ResetBody,
    db: Session = Depends(get_db),
    username: str = Depends(require_dashboard_session),
):
    """Kosongkan data bisnis demo (bisnis dan API key-nya tetap ada). Hanya bisnis demo, perlu confirm=true."""
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Konfirmasi diperlukan.")
    if _busy.locked():
        raise HTTPException(status_code=409, detail="Aksi lain sedang berjalan.")
    async with _busy:
        business = _demo_business(db)
        if not business.is_demo:  # sabuk pengaman kedua; _demo_business sudah memastikannya
            raise HTTPException(status_code=403, detail="Bukan bisnis demo.")
        counts = _reset_counts(db, business)
        sources = db.query(Source).filter(Source.business_id == business.id).all()
        for source in sources:
            if source.deleted_at is None:
                trash_service.trash_source(db, source, deleted_by=username)
            trash_service.purge_source(db, source, deleted_by=username, reason="Reset demo Panggung")
        from app.models.lab_entry import LabEntry
        db.query(LabEntry).filter(LabEntry.business_id == business.id).delete(synchronize_session=False)
        db.commit()
    return ControlResultOut(
        ok=True,
        message=f"Data demo dikosongkan: {counts.datasets} dataset, {counts.batches} batch, {counts.transactions} transaksi",
    )
