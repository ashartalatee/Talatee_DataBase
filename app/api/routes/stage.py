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
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Batch, Business, CoreTransaction, Dataset, File as FileModel, Source
from app.schemas.stage import (
    FeedItem,
    FlowCount,
    FlowTrust,
    NameValue,
    StageFlow,
    StageSummaryOut,
    TrendDay,
)
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
        _batches(db, Batch, Dataset.trust_status, FileModel.filename)
        .outerjoin(FileModel, FileModel.batch_id == Batch.id)
        .order_by(Batch.started_at.desc())
        .limit(15)
        .all()
    )
    for batch, status, filename in recent:
        name = filename or "file"
        if batch.status == "failed":
            text, tone = f"{name} gagal diproses", "y"
        else:
            text = f"{name}: {batch.records_saved} baris, {_TRUST_LABEL.get(status, str(status).lower())}"
            tone = _TRUST_TONE.get(status, "b")
        feed.append(FeedItem(t=_ms(batch.started_at) or 0, text=text, tone=tone))

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
        hermes_connected=False,
    )
