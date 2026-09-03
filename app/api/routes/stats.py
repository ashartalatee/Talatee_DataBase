from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch, Dataset, File as FileModel, Source
from app.schemas.stats import OverviewStatsOut, RecentBatchItem, SourceBreakdownItem

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(require_dashboard_session)])


@router.get("/overview", response_model=OverviewStatsOut)
def get_overview_stats(db: Session = Depends(get_db)):
    """
    Agregasi ringkas untuk halaman Overview dashboard. Semua angka dihitung
    dari metadata DB (Prinsip Inti #4: API selalu baca dari Postgres, tidak
    pernah scan langsung ke raw storage).
    """
    total_sources = db.query(func.count(Source.id)).scalar() or 0
    total_datasets = db.query(func.count(Dataset.id)).scalar() or 0
    total_batches = db.query(func.count(Batch.id)).scalar() or 0
    total_records = db.query(func.coalesce(func.sum(Batch.records_saved), 0)).scalar() or 0
    total_storage_bytes = db.query(func.coalesce(func.sum(FileModel.file_size), 0)).scalar() or 0

    # Breakdown records per source (untuk pie chart)
    breakdown_rows = (
        db.query(
            Source.id,
            Source.name,
            func.coalesce(func.sum(Batch.records_saved), 0),
        )
        .outerjoin(Dataset, Dataset.source_id == Source.id)
        .outerjoin(Batch, Batch.dataset_id == Dataset.id)
        .group_by(Source.id, Source.name)
        .all()
    )
    data_by_source = [
        SourceBreakdownItem(source_id=str(sid), source_name=name, total_records=total)
        for sid, name, total in breakdown_rows
        if total > 0
    ]

    # 10 batch terbaru (untuk "Recently Added Data")
    recent_rows = (
        db.query(Batch, Dataset.name, Source.name, FileModel.filename)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .outerjoin(FileModel, FileModel.batch_id == Batch.id)
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
        total_datasets=total_datasets,
        total_sources=total_sources,
        total_batches=total_batches,
        total_storage_bytes=total_storage_bytes,
        data_by_source=data_by_source,
        recent_batches=recent_batches,
    )
