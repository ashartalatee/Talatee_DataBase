from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch, Business, CoreTransaction, Dataset, File as FileModel, Source
from app.schemas.stats import OverviewStatsOut, RecentBatchItem, SourceBreakdownItem

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(require_dashboard_session)])

# Filter "tidak sedang di Sampah" dipakai berkali-kali di bawah — batch,
# dataset, source, DAN business-nya harus sama-sama tidak di-trash (lihat
# aturan visibilitas berjenjang di app/services/trash.py) supaya angka
# Overview tidak ikut menghitung data yang lagi disembunyikan.
_NOT_TRASHED = (
    Batch.deleted_at.is_(None),
    Dataset.deleted_at.is_(None),
    Source.deleted_at.is_(None),
    Business.deleted_at.is_(None),
)


@router.get("/overview", response_model=OverviewStatsOut)
def get_overview_stats(db: Session = Depends(get_db)):
    """
    Agregasi ringkas untuk halaman Overview dashboard. Semua angka dihitung
    dari metadata DB (Prinsip Inti #4: API selalu baca dari Postgres, tidak
    pernah scan langsung ke raw storage). Item yang sedang di Sampah (hapus
    sesaat, di level mana pun -- business/source/dataset/batch) TIDAK ikut
    dihitung di angka mana pun di sini.
    """
    total_sources = (
        db.query(func.count(Source.id))
        .join(Business, Source.business_id == Business.id)
        .filter(Source.deleted_at.is_(None), Business.deleted_at.is_(None))
        .scalar()
        or 0
    )
    total_datasets = (
        db.query(func.count(Dataset.id))
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(Dataset.deleted_at.is_(None), Source.deleted_at.is_(None), Business.deleted_at.is_(None))
        .scalar()
        or 0
    )

    trusted_datasets = (
        db.query(func.count(Dataset.id))
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(
            Dataset.deleted_at.is_(None),
            Source.deleted_at.is_(None),
            Business.deleted_at.is_(None),
            Dataset.trust_status == "TRUSTED",
        )
        .scalar()
        or 0
    )
    batch_chain = (
        db.query(Batch)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(*_NOT_TRASHED)
    )
    total_batches = batch_chain.with_entities(func.count(Batch.id)).scalar() or 0
    total_records = (
        batch_chain.with_entities(func.coalesce(func.sum(Batch.records_saved), 0)).scalar() or 0
    )

    total_storage_bytes = (
        db.query(func.coalesce(func.sum(FileModel.file_size), 0))
        .join(Batch, FileModel.batch_id == Batch.id)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(*_NOT_TRASHED)
        .scalar()
        or 0
    )

    # Omzet (Rupiah) TOTAL keseluruhan -- cuma baris is_revenue=True yang
    # dihitung (lihat REVENUE_STATUSES di app/models/core_transaction.py).
    # Ini beda dari total_records: total_records = jumlah baris file yang
    # tersimpan, total_revenue = nilai transaksi yang benar-benar dianggap
    # closing/berhasil.
    total_revenue = (
        db.query(func.coalesce(func.sum(CoreTransaction.subtotal), 0))
        .join(Batch, CoreTransaction.batch_id == Batch.id)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(CoreTransaction.is_revenue.is_(True), Dataset.trust_status == "TRUSTED", *_NOT_TRASHED)
        .scalar()
    )
    total_revenue = float(total_revenue or 0)

    # Omzet per Source (channel) -- query TERPISAH dari breakdown_rows di
    # bawah (bukan digabung satu query) supaya join ke CoreTransaction tidak
    # bikin fan-out yang merusak SUM(Batch.records_saved).
    revenue_by_source_rows = (
        db.query(Source.id, func.coalesce(func.sum(CoreTransaction.subtotal), 0))
        .join(Dataset, (Dataset.source_id == Source.id) & (Dataset.deleted_at.is_(None)) & (Dataset.trust_status == "TRUSTED"))
        .join(Batch, (Batch.dataset_id == Dataset.id) & (Batch.deleted_at.is_(None)))
        .join(CoreTransaction, (CoreTransaction.batch_id == Batch.id) & (CoreTransaction.is_revenue.is_(True)))
        .filter(Source.deleted_at.is_(None))
        .group_by(Source.id)
        .all()
    )
    revenue_by_source = {str(sid): float(rev) for sid, rev in revenue_by_source_rows}

    # Breakdown records per source (untuk pie chart)
    breakdown_rows = (
        db.query(
            Source.id,
            Source.name,
            func.coalesce(func.sum(Batch.records_saved), 0),
        )
        .join(Business, Source.business_id == Business.id)
        .filter(Source.deleted_at.is_(None), Business.deleted_at.is_(None))
        .outerjoin(
            Dataset,
            (Dataset.source_id == Source.id) & (Dataset.deleted_at.is_(None)),
        )
        .outerjoin(
            Batch,
            (Batch.dataset_id == Dataset.id) & (Batch.deleted_at.is_(None)),
        )
        .group_by(Source.id, Source.name)
        .all()
    )
    data_by_source = [
        SourceBreakdownItem(
            source_id=str(sid),
            source_name=name,
            total_records=total,
            total_revenue=revenue_by_source.get(str(sid), 0.0),
        )
        for sid, name, total in breakdown_rows
        if total > 0
    ]

    # 10 batch terbaru (untuk "Recently Added Data")
    recent_rows = (
        db.query(Batch, Dataset.name, Source.name, FileModel.filename)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .outerjoin(FileModel, FileModel.batch_id == Batch.id)
        .filter(*_NOT_TRASHED)
        .order_by(Batch.started_at.desc())
        .limit(10)
        .all()
    )
    recent_batches = [
        RecentBatchItem(
            id=str(batch.id),
            dataset_name=dataset_name,
            source_name=source_name,
            filename=filename or "-",
            status=batch.status,
            records_saved=batch.records_saved,
            started_at=batch.started_at.isoformat(),
        )
        for batch, dataset_name, source_name, filename in recent_rows
    ]

    return OverviewStatsOut(
        total_records=total_records,
        total_revenue=total_revenue,
        total_datasets=total_datasets,
        trusted_datasets=trusted_datasets,
        untrusted_datasets=total_datasets - trusted_datasets,
        total_sources=total_sources,
        total_batches=total_batches,
        total_storage_bytes=total_storage_bytes,
        data_by_source=data_by_source,
        recent_batches=recent_batches,
    )
