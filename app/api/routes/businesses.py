import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch, Business, Dataset, Source
from app.models.business import BUSINESS_CATEGORIES
from app.schemas.business import BusinessListItemOut, BusinessOut
from app.schemas.source import SourceOut
from app.schemas.trash import DeletionLogOut, PurgeRequest
from app.services import trash as trash_service

router = APIRouter(prefix="/businesses", tags=["businesses"], dependencies=[Depends(require_dashboard_session)])


@router.get("/categories", response_model=list[str])
def list_business_categories():
    """Daftar tetap kategori business (dropdown) — dipakai UI, bukan free text."""
    return BUSINESS_CATEGORIES


@router.get("", response_model=list[BusinessListItemOut])
def list_businesses(db: Session = Depends(get_db)):
    # Business yang di-trash TIDAK ikut muncul di sini sama sekali (bukan
    # cuma dikosongkan angkanya) -- lihat POST /businesses/{id}/trash.
    # Hitungan total_sources/total_datasets/total_records juga TIDAK boleh
    # ikut menghitung source/dataset/batch yang lagi di-trash, biar angka di
    # kartu business tidak "berbohong" padahal Source/Dataset-nya sudah
    # tidak bisa diklik (404).
    rows = (
        db.query(
            Business,
            func.count(func.distinct(Source.id)),
            func.count(func.distinct(Dataset.id)),
            func.coalesce(func.sum(Batch.records_saved), 0),
        )
        .filter(Business.deleted_at.is_(None))
        .outerjoin(Source, (Source.business_id == Business.id) & (Source.deleted_at.is_(None)))
        .outerjoin(Dataset, (Dataset.source_id == Source.id) & (Dataset.deleted_at.is_(None)))
        .outerjoin(Batch, (Batch.dataset_id == Dataset.id) & (Batch.deleted_at.is_(None)))
        .group_by(Business.id)
        .order_by(Business.created_at.desc())
        .all()
    )
    return [
        BusinessListItemOut(
            id=b.id,
            name=b.name,
            category=b.category,
            status=b.status,
            created_at=b.created_at,
            total_sources=total_sources,
            total_datasets=total_datasets,
            total_records=total_records,
        )
        for b, total_sources, total_datasets, total_records in rows
    ]


@router.get("/{business_id}", response_model=BusinessOut)
def get_business(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if business is None or business.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Business tidak ditemukan")
    return business


@router.get("/{business_id}/sources", response_model=list[SourceOut])
def list_business_sources(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if business is None or business.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Business tidak ditemukan")
    # Source yang di-trash tidak boleh ikut muncul di sini.
    return trash_service.visible_sources_query(db).filter(Source.business_id == business_id).all()


@router.post("/{business_id}/trash", response_model=BusinessOut)
def trash_business(business_id: uuid.UUID, db: Session = Depends(get_db), username: str = Depends(require_dashboard_session)):
    """Pindahkan business (beserta SEMUA source/dataset/batch di bawahnya)
    ke Sampah. Level paling atas -- trash di sini menyembunyikan seluruh
    data client ini dari dashboard, tapi tetap bisa dipulihkan penuh lewat
    /restore selama belum di-hapus-permanen."""
    business = db.get(Business, business_id)
    if business is None or business.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Business tidak ditemukan")
    trash_service.trash_business(db, business, deleted_by=username)
    return business


@router.post("/{business_id}/restore", response_model=BusinessOut)
def restore_business(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if business is None or business.deleted_at is None:
        raise HTTPException(status_code=404, detail="Business tidak ada di Sampah")
    trash_service.restore_business(db, business)
    return business


@router.delete("/{business_id}/permanent", response_model=DeletionLogOut)
def purge_business(business_id: uuid.UUID, body: PurgeRequest, db: Session = Depends(get_db), username: str = Depends(require_dashboard_session)):
    """HAPUS PERMANEN — wajib ketik ulang nama business di `confirm_name`.
    SEMUA source/dataset/batch/file/core_transactions/correction/
    reconciliation/connector di bawah business ini ikut terhapus permanen,
    termasuk objeknya di MinIO. Tidak bisa dibatalkan."""
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business tidak ditemukan")
    if business.deleted_at is None:
        raise HTTPException(
            status_code=400,
            detail="Business harus dipindahkan ke Sampah dulu sebelum bisa dihapus permanen.",
        )
    if body.confirm_name != business.name:
        raise HTTPException(
            status_code=400,
            detail="confirm_name tidak cocok dengan nama business — hapus permanen dibatalkan.",
        )
    return trash_service.purge_business(db, business, deleted_by=username, reason=body.reason)
