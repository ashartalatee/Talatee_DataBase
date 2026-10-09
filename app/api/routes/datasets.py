import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch, Business, Dataset, Source
from app.schemas.batch import BatchOut
from app.schemas.dataset import DatasetDetailOut, DatasetListItemOut
from app.schemas.trash import DeletionLogOut, PurgeRequest
from app.services import trash as trash_service

router = APIRouter(prefix="/datasets", tags=["datasets"], dependencies=[Depends(require_dashboard_session)])


@router.get("", response_model=list[DatasetListItemOut])
def list_datasets(
    trust: Literal["all", "trusted", "untrusted"] = Query("all"),
    db: Session = Depends(get_db),
):
    """List semua dataset dengan info ringkas: total records (jumlah
    records_saved dari semua batch sukses & TIDAK di-trash) dan total
    batches. Dataset yang ada di Sampah, atau source induknya ada di
    Sampah, tidak ikut muncul di sini — lihat GET /trash untuk itu.

    Parameter `trust` (default "all" = perilaku lama, tidak merusak
    pemanggil yang sudah ada):
      - "trusted"   -> hanya dataset berstatus TRUSTED (dipakai Data Explorer
                       / Clients: hanya data yang sudah lolos validasi)
      - "untrusted" -> hanya yang BELUM TRUSTED (wilayah Eksperimen)
      - "all"       -> semuanya (dipakai form Laboratorium untuk memilih
                       dataset yang mau ditautkan ke eksperimen)
    """
    base = trash_service.visible_datasets_query(db)
    if trust == "trusted":
        base = base.filter(Dataset.trust_status == "TRUSTED")
    elif trust == "untrusted":
        base = base.filter(Dataset.trust_status != "TRUSTED")

    rows = (
        base.add_columns(
            func.coalesce(func.sum(Batch.records_saved), 0).label("total_records"),
            func.count(Batch.id).label("total_batches"),
        )
        .outerjoin(
            Batch,
            (Batch.dataset_id == Dataset.id) & (Batch.deleted_at.is_(None)),
        )
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
            trust_status=ds.trust_status,
        )
        for ds, total_records, total_batches in rows
    ]


@router.get("/{dataset_id}", response_model=DatasetDetailOut)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """Detail satu dataset + riwayat batch-nya yang TIDAK di-trash (terbaru
    dulu). Batch yang di-trash tetap ada di DB tapi disembunyikan dari sini
    — untuk melihat/restore-nya, buka halaman Sampah."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    source = db.get(Source, dataset.source_id)
    business = db.get(Business, source.business_id) if source else None

    batches = (
        db.query(Batch)
        .filter(Batch.dataset_id == dataset_id, Batch.deleted_at.is_(None))
        .order_by(Batch.started_at.desc())
        .all()
    )

    return DatasetDetailOut(
        id=dataset.id,
        source_id=dataset.source_id,
        name=dataset.name,
        description=dataset.description,
        business_name=business.name if business else "",
        source_name=source.name if source else "",
        schema_=dataset.schema_,
        trust_status=dataset.trust_status,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        batches=[BatchOut.model_validate(b) for b in batches],
    )


@router.post("/{dataset_id}/trash", response_model=DatasetListItemOut)
def trash_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db), username: str = Depends(require_dashboard_session)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    trash_service.trash_dataset(db, dataset, deleted_by=username)
    return DatasetListItemOut(
        id=dataset.id,
        source_id=dataset.source_id,
        name=dataset.name,
        description=dataset.description,
        updated_at=dataset.updated_at,
        total_records=0,
        total_batches=0,
        trust_status=dataset.trust_status,
    )


@router.post("/{dataset_id}/restore", response_model=DatasetListItemOut)
def restore_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.deleted_at is None:
        raise HTTPException(status_code=404, detail="Dataset tidak ada di Sampah")
    trash_service.restore_dataset(db, dataset)
    total_records = (
        db.query(func.coalesce(func.sum(Batch.records_saved), 0))
        .filter(Batch.dataset_id == dataset.id, Batch.deleted_at.is_(None))
        .scalar()
        or 0
    )
    total_batches = (
        db.query(func.count(Batch.id))
        .filter(Batch.dataset_id == dataset.id, Batch.deleted_at.is_(None))
        .scalar()
        or 0
    )
    return DatasetListItemOut(
        id=dataset.id,
        source_id=dataset.source_id,
        name=dataset.name,
        description=dataset.description,
        updated_at=dataset.updated_at,
        total_records=total_records,
        total_batches=total_batches,
        trust_status=dataset.trust_status,
    )


@router.delete("/{dataset_id}/permanent", response_model=DeletionLogOut)
def purge_dataset(dataset_id: uuid.UUID, body: PurgeRequest, db: Session = Depends(get_db), username: str = Depends(require_dashboard_session)):
    """HAPUS PERMANEN — wajib ketik ulang nama dataset di `confirm_name`.
    Semua batch/file/core_transactions/correction/reconciliation di bawah
    dataset ini ikut terhapus permanen."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    if dataset.deleted_at is None:
        raise HTTPException(
            status_code=400,
            detail="Dataset harus dipindahkan ke Sampah dulu sebelum bisa dihapus permanen.",
        )
    if body.confirm_name != dataset.name:
        raise HTTPException(
            status_code=400,
            detail="confirm_name tidak cocok dengan nama dataset — hapus permanen dibatalkan.",
        )
    return trash_service.purge_dataset(db, dataset, deleted_by=username, reason=body.reason)
