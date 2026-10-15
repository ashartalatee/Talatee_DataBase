"""
Ringkasan untuk Panggung (/stage): HANYA bisnis demo (Business.is_demo = true).

Aturan yang dijaga di sini:
- Hanya membaca dari metadata/Core di Postgres (Prinsip Inti #4), tidak menyentuh MinIO.
- Hanya bisnis demo. Data bisnis non-demo tidak pernah ikut dihitung.
- Item yang sedang di Sampah (batch/dataset/source/business) tidak ikut dihitung.
- Angka uang (omzet, kategori, channel) hanya dari dataset berstatus TRUSTED dan batch yang tidak gagal.
- Tidak mengembalikan teks galat mentah, kunci, atau alamat internal: panel ini tampil saat siaran.
- Dilindungi sesi dashboard, sama seperti /stats dan /showcase.

"Channel" = nama Source (mis. "Shopee", "Upload manual"). Stok dan log Hermes belum punya
tabel di backend, jadi dikembalikan kosong (hermes_connected = false).
"""
import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Batch, Business, CoreTransaction, Dataset, File as FileModel, Source
from app.schemas.stage import (
    AgentState,
    ApiInfo,
    BatchItem,
    EventItem,
    FeedItem,
    FlowCount,
    FlowTrust,
    NameValue,
    StageFlow,
    StageSummaryOut,
    TrendDay,
)
from app.services.stage_activity import ActivityRow, build_activity
from app.services.stage_batches import gudang_status
from app.api.routes import batches as batches_routes, core as core_routes
from app.models.api_key import ApiKey
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(
    prefix="/stage",
    tags=["stage"],
    dependencies=[Depends(require_dashboard_session)],
)

WINDOW_DAYS = 30
_VISIBLE = (
    Batch.deleted_at.is_(None),
    Dataset.deleted_at.is_(None),
    Source.deleted_at.is_(None),
    Business.deleted_at.is_(None),
    Business.is_demo.is_(True),
)
_TRUST_LABEL = {
    "TRUSTED": "terpercaya",
    "NEEDS_REVIEW": "perlu ditinjau",
    "VALIDATING": "divalidasi",
    "INGESTED": "baru masuk",
}
_TRUST_TONE = {"TRUSTED": "g", "NEEDS_REVIEW": "y"}


def _ms(dt: datetime | None) -> int | None:
    return int(dt.timestamp() * 1000) if dt else None


def _batches(db: Session, *entities):
    """Rantai Batch -> Dataset -> Source -> Business, hanya bisnis demo yang terlihat."""
    return (
        db.query(*entities)
        .select_from(Batch)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(*_VISIBLE)
    )


def _revenue(db: Session, since: date, *entities):
    """Baris Core yang dihitung sebagai omzet: demo, TRUSTED, is_revenue, dalam jendela 30 hari."""
    return (
        db.query(*entities)
        .select_from(CoreTransaction)
        .join(Batch, CoreTransaction.batch_id == Batch.id)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(
            *_VISIBLE,
            Dataset.trust_status == "TRUSTED",
            Batch.status.in_(("success", "partial_failed")),  # batch gagal tidak ikut dihitung
            CoreTransaction.is_revenue.is_(True),
            CoreTransaction.transaction_date >= since,
        )
    )


@router.get("/summary", response_model=StageSummaryOut)
def get_stage_summary(db: Session = Depends(get_db)):
    today = date.today()
    since = today - timedelta(days=WINDOW_DAYS - 1)

    # --- alur: file, batch, status kepercayaan (status batch = status dataset-nya) ---
    file_count = _batches(db, func.count(FileModel.id)).join(FileModel, FileModel.batch_id == Batch.id).scalar() or 0
    batch_count, last_batch = _batches(db, func.count(Batch.id), func.max(Batch.started_at)).one()
    trust_rows = _batches(db, Dataset.trust_status, func.count(Batch.id)).group_by(Dataset.trust_status).all()
    last_trust = _batches(db, func.max(Dataset.updated_at)).scalar()
    trust = {"INGESTED": 0, "VALIDATING": 0, "NEEDS_REVIEW": 0, "TRUSTED": 0}
    for status, n in trust_rows:
        if status in trust:
            trust[status] = int(n)

    # --- tren 30 hari (hari tanpa transaksi diisi 0 supaya grafik tidak melompat) ---
    per_day = {
        d: (float(rev or 0), int(orders or 0))
        for d, rev, orders in _revenue(
            db,
            since,
            CoreTransaction.transaction_date,
            func.coalesce(func.sum(CoreTransaction.subtotal), 0),
            func.count(func.distinct(CoreTransaction.order_id)),
        )
        .group_by(CoreTransaction.transaction_date)
        .all()
    }
    trend = []
    for i in range(WINDOW_DAYS):
        rev, orders = per_day.get(since + timedelta(days=i), (0.0, 0))
        trend.append(TrendDay(d=str(i + 1), rev=rev, ord=orders))

    # --- kategori dan channel (channel = nama source) ---
    cat = func.coalesce(CoreTransaction.category, "Lainnya")
    total = func.coalesce(func.sum(CoreTransaction.subtotal), 0)
    categories = [
        NameValue(name=name, value=float(v or 0))
        for name, v in _revenue(db, since, cat, total).group_by(cat).order_by(total.desc()).all()
    ]
    channels = [
        NameValue(name=name, value=float(v or 0))
        for name, v in _revenue(db, since, Source.name, total).group_by(Source.name).order_by(total.desc()).all()
    ]

    # --- aktivitas terbaru: dari batch demo, tanpa pesan galat mentah ---
    feed = []
    recent = (
        _batches(db, Batch, Dataset.trust_status, FileModel.filename, Dataset.updated_at, Source.name)
        .outerjoin(FileModel, FileModel.batch_id == Batch.id)
        .order_by(Batch.started_at.desc())
        .limit(15)
        .all()
    )
    for batch, status, filename, ds_updated, channel in recent:
        name = filename or "file"
        if batch.status == "failed":
            text, tone = f"{name} gagal diproses", "y"
        else:
            text = f"{name}: {batch.records_saved} baris, {_TRUST_LABEL.get(status, str(status).lower())}"
            tone = _TRUST_TONE.get(status, "b")
        feed.append(FeedItem(t=_ms(batch.started_at) or 0, text=text, tone=tone))

    # --- kejadian dan langkah agen: diturunkan dari status batch dan dataset yang nyata ---
    now_ms = int(datetime.now().timestamp() * 1000)
    events, agent = build_activity(
        [
            ActivityRow(
                batch_id=str(batch.id), dataset_id=str(batch.dataset_id), filename=filename or "file",
                channel=channel, batch_status=batch.status, records=int(batch.records_saved or 0),
                trust=status, started_ms=_ms(batch.started_at) or 0,
                finished_ms=_ms(batch.finished_at), updated_ms=_ms(ds_updated),
            )
            for batch, status, filename, ds_updated, channel in recent
        ],
        now_ms,
    )

    # --- daftar file Gudang Data (hanya bisnis demo) dan info koneksi API ---
    batches = [
        BatchItem(
            id=str(b.id), file=filename or "file", channel=channel, rows=int(b.records_saved or 0),
            status=gudang_status(b.status, status, now_ms - max(_ms(b.started_at) or 0, _ms(ds_updated) or 0)),
            trust=status or "", t=_ms(b.started_at) or 0,
        )
        for b, status, filename, ds_updated, channel in recent
    ]
    demo_biz = db.query(Business.id).filter(Business.is_demo.is_(True), Business.deleted_at.is_(None)).first()
    key = (
        db.query(ApiKey)
        .filter(ApiKey.business_id == demo_biz[0], ApiKey.status == "active")
        .order_by(ApiKey.created_at.desc())
        .first()
        if demo_biz
        else None
    )
    api_info = ApiInfo(
        configured=key is not None,
        key_prefix=key.key_prefix if key else None,
        last_used=_ms(key.last_used_at) if key else None,
    )

    return StageSummaryOut(
        flow=StageFlow(
            file=FlowCount(count=int(file_count), last=_ms(last_batch)),
            batch=FlowCount(count=int(batch_count or 0), last=_ms(last_batch)),
            trust=FlowTrust(**trust, last=_ms(last_trust)),
            question=FlowCount(),
            answer=FlowCount(),
        ),
        trend=trend,
        categories=categories,
        channels=channels,
        low_stock=[],
        hermes=[],
        feed=feed,
        events=events,
        agent=agent,
        batches=batches,
        api=api_info,
        hermes_connected=False,
    )


def _demo_batch_or_404(db: Session, batch_id: uuid.UUID) -> Batch:
    """Batch harus milik bisnis demo yang tidak di Sampah. Batch bisnis lain diperlakukan seperti tidak ada."""
    batch = _batches(db, Batch).filter(Batch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch demo tidak ditemukan")
    return batch


@router.get("/batches/{batch_id}")
def get_stage_batch(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    """Isi mentah, laporan masalah, dan versi bersih satu batch DEMO (read-only), memakai fungsi yang sudah ada."""
    batch = _demo_batch_or_404(db, batch_id)
    return {
        "dataset_id": str(batch.dataset_id),
        "raw": batches_routes.get_batch_rows(batch_id, 40, db),
        "issues": batches_routes.get_batch_issues(batch_id, db),
        "clean": batches_routes.get_batch_clean(batch_id, db),
    }


@router.post("/batches/{batch_id}/promote")
def promote_stage_batch(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    """Tandai dataset batch DEMO ini terpercaya lewat jalur dan aturan yang sama (promote_dataset)."""
    batch = _demo_batch_or_404(db, batch_id)
    try:
        core_routes.get_dataset_quality(batch.dataset_id, db)  # segarkan status dari hasil validasi terbaru
        core_routes.promote_dataset(batch.dataset_id, db)
    except HTTPException:
        raise HTTPException(status_code=409, detail="Belum bisa ditandai terpercaya: masih ada masalah yang perlu ditinjau.") from None
    return {"ok": True, "trust_status": "TRUSTED"}
