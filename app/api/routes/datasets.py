import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Batch, Dataset
from app.schemas.batch import BatchOut
from app.schemas.dataset import DatasetDetailOut, DatasetListItemOut

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetListItemOut])
def list_datasets(db: Session = Depends(get_db)):
    """List semua dataset dengan info ringkas: total records (jumlah
    records_saved dari semua batch sukses) dan total batches."""
    rows = (
        db.query(
            Dataset,
            func.coalesce(func.sum(Batch.records_saved), 0).label("total_records"),
            func.count(Batch.id).label("total_batches"),
        )
        .outerjoin(Batch, Batch.dataset_id == Dataset.id)
        .group_by(Dataset.id)
        .order_by(Dataset.updated_at.desc())
        .all()
    )

    return [
        DatasetListItemOut(
            id=ds.id,
            source_id=ds.source_id,
            name=ds.name,
            description=ds.description,
            updated_at=ds.updated_at,
            total_records=total_records,
            total_batches=total_batches,
        )
        for ds, total_records, total_batches in rows
    ]


@router.get("/{dataset_id}", response_model=DatasetDetailOut)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """Detail satu dataset + riwayat batch-nya (terbaru dulu)."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    batches = (
        db.query(Batch)
        .filter(Batch.dataset_id == dataset_id)
        .order_by(Batch.started_at.desc())
        .all()
    )

    return DatasetDetailOut(
        id=dataset.id,
        source_id=dataset.source_id,
        name=dataset.name,
        description=dataset.description,
        schema_=dataset.schema_,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        batches=[BatchOut.model_validate(b) for b in batches],
    )
