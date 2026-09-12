import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Source
from app.schemas.source import SourceOut
from app.schemas.trash import DeletionLogOut, PurgeRequest
from app.services import trash as trash_service

router = APIRouter(prefix="/sources", tags=["sources"], dependencies=[Depends(require_dashboard_session)])


@router.get("", response_model=list[SourceOut])
def list_sources(business_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    query = trash_service.visible_sources_query(db)
    if business_id is not None:
        query = query.filter(Source.business_id == business_id)
    return query.order_by(Source.created_at.desc()).all()


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: uuid.UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None or not trash_service.is_source_visible(db, source):
        raise HTTPException(status_code=404, detail="Source tidak ditemukan")
    return source


@router.post("/{source_id}/trash", response_model=SourceOut)
def trash_source(source_id: uuid.UUID, db: Session = Depends(get_db), username: str = Depends(require_dashboard_session)):
    """Pindahkan source (beserta semua dataset & batch di bawahnya) ke
    Sampah. Anak-anaknya TIDAK ditandai deleted_at satu-satu — mereka ikut
    hilang dari tampilan karena visibilitas dicek berantai sampai ke source
    (lihat app/services/trash.py). Bisa dipulihkan kapan saja lewat
    /restore selama belum di-hapus-permanen."""
    source = db.get(Source, source_id)
    if source is None or source.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Source tidak ditemukan")
    trash_service.trash_source(db, source, deleted_by=username)
    return source


@router.post("/{source_id}/restore", response_model=SourceOut)
def restore_source(source_id: uuid.UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None or source.deleted_at is None:
        raise HTTPException(status_code=404, detail="Source tidak ada di Sampah")
    trash_service.restore_source(db, source)
    return source


@router.delete("/{source_id}/permanent", response_model=DeletionLogOut)
def purge_source(source_id: uuid.UUID, body: PurgeRequest, db: Session = Depends(get_db), username: str = Depends(require_dashboard_session)):
    """HAPUS PERMANEN — tidak bisa dibatalkan. Hanya bisa dilakukan pada
    source yang SUDAH ada di Sampah (deleted_at terisi), dan wajib ketik
    ulang nama source-nya persis di `confirm_name` supaya tidak ke-klik
    tanpa sengaja. Semua dataset/batch/file/core_transactions di bawahnya
    ikut terhapus permanen, termasuk objeknya di MinIO."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source tidak ditemukan")
    if source.deleted_at is None:
        raise HTTPException(
            status_code=400,
            detail="Source harus dipindahkan ke Sampah dulu sebelum bisa dihapus permanen.",
        )
    if body.confirm_name != source.name:
        raise HTTPException(
            status_code=400,
            detail="confirm_name tidak cocok dengan nama source — hapus permanen dibatalkan.",
        )
    return trash_service.purge_source(db, source, deleted_by=username, reason=body.reason)
