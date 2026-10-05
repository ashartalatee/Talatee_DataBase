import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ingestion.file_rows import read_rows
from app.ingestion.issue_checks import check_rows
from app.ingestion.clean_rows import clean_rows
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch
from app.models import File as FileModel
from app.schemas.batch import BatchDetailOut, BatchOut, FileOut
from app.schemas.trash import DeletionLogOut, PurgeRequest
from app.services import trash as trash_service
from app.storage.minio_client import get_file

router = APIRouter(tags=["batches"], dependencies=[Depends(require_dashboard_session)])


@router.get("/batches", response_model=list[BatchOut])
def list_batches(
    dataset_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
):
    query = trash_service.visible_batches_query(db)
    if dataset_id is not None:
        query = query.filter(Batch.dataset_id == dataset_id)
    return query.order_by(Batch.started_at.desc()).all()


@router.get("/batches/{batch_id}", response_model=BatchDetailOut)
def get_batch(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")

    files = db.query(FileModel).filter(FileModel.batch_id == batch_id).all()
    return BatchDetailOut(
        **BatchOut.model_validate(batch).model_dump(),
        files=[FileOut.model_validate(f) for f in files],
    )


@router.get("/batches/{batch_id}/rows")
def get_batch_rows(batch_id: uuid.UUID, limit: int = 500, db: Session = Depends(get_db)):
    """Tampilkan isi file mentah apa adanya (read-only), untuk dilihat manusia.
    Semua nilai dikembalikan sebagai teks, tanpa pembersihan atau konversi."""
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")

    file_row = db.query(FileModel).filter(FileModel.batch_id == batch_id).first()
    if file_row is None:
        raise HTTPException(status_code=404, detail="Batch ini tidak punya file")

    try:
        data = get_file(file_row.storage_path)
    except Exception:
        raise HTTPException(status_code=502, detail="File mentah tidak bisa dibaca dari storage")

    rows = read_rows(data, file_row.filename)
    if not rows:
        raise HTTPException(status_code=422, detail="Format file tidak dikenali (harus .csv atau .xlsx)")

    def to_text(v):
        return "" if v is None else str(v)

    columns = [to_text(c) for c in rows[0]]
    body = rows[1:]
    limit = max(1, min(limit, 2000))
    shown = body[:limit]

    return {
        "filename": file_row.filename,
        "total_rows": len(body),
        "shown_rows": len(shown),
        "truncated": len(body) > len(shown),
        "columns": columns,
        "rows": [[to_text(c) for c in r] for r in shown],
    }


@router.post("/batches/{batch_id}/trash", response_model=BatchOut)
def trash_batch(batch_id: uuid.UUID, db: Session = Depends(get_db), username: str = Depends(require_dashboard_session)):
    """Pindahkan SATU batch (= satu kali upload) ke Sampah. Langsung hilang
    dari dashboard/laporan/insight (dataset otomatis diproses ulang di
    belakang layar), tapi file mentahnya di MinIO & barisnya di DB tetap
    ada — bisa dipulihkan lewat /restore kapan saja."""
    batch = db.get(Batch, batch_id)
    if batch is None or batch.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")
    trash_service.trash_batch(db, batch, deleted_by=username)
    return batch


@router.post("/batches/{batch_id}/restore", response_model=BatchOut)
def restore_batch(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if batch is None or batch.deleted_at is None:
        raise HTTPException(status_code=404, detail="Batch tidak ada di Sampah")
    trash_service.restore_batch(db, batch)
    return batch


@router.delete("/batches/{batch_id}/permanent", response_model=DeletionLogOut)
def purge_batch(batch_id: uuid.UUID, body: PurgeRequest, db: Session = Depends(get_db), username: str = Depends(require_dashboard_session)):
    """HAPUS PERMANEN satu batch — wajib isi `confirm_name` dengan nama file
    aslinya (lihat GET /batches/{id} -> files[0].filename) supaya tidak
    ke-klik tanpa sengaja. File di MinIO + baris DB + core_transactions
    terkait ikut terhapus, tidak bisa dikembalikan lagi setelah ini."""
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")
    if batch.deleted_at is None:
        raise HTTPException(
            status_code=400,
            detail="Batch harus dipindahkan ke Sampah dulu sebelum bisa dihapus permanen.",
        )
    files = db.query(FileModel).filter(FileModel.batch_id == batch.id).all()
    expected_names = {f.filename for f in files} | {f"Batch {batch.started_at:%Y-%m-%d %H:%M} ({batch.status})"}
    if body.confirm_name not in expected_names:
        raise HTTPException(
            status_code=400,
            detail="confirm_name tidak cocok dengan nama file batch ini — hapus permanen dibatalkan.",
        )
    return trash_service.purge_batch(db, batch, deleted_by=username, reason=body.reason)


@router.get("/files/{file_id}/download")
def download_file(file_id: uuid.UUID, db: Session = Depends(get_db)):
    file_row = db.get(FileModel, file_id)
    if file_row is None:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    data = get_file(file_row.storage_path)
    return StreamingResponse(
        iter([data]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file_row.filename}"'},
    )


@router.get("/batches/{batch_id}/issues")
def get_batch_issues(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    """Laporan masalah kualitas data (read-only). Tidak mengubah apa pun."""
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")

    file_row = db.query(FileModel).filter(FileModel.batch_id == batch_id).first()
    if file_row is None:
        raise HTTPException(status_code=404, detail="Batch ini tidak punya file")

    try:
        data = get_file(file_row.storage_path)
    except Exception:
        raise HTTPException(status_code=502, detail="File mentah tidak bisa dibaca dari storage")

    rows = read_rows(data, file_row.filename)
    if not rows:
        raise HTTPException(status_code=422, detail="Format file tidak dikenali (harus .csv atau .xlsx)")

    to_text = lambda v: "" if v is None else str(v)
    columns = [to_text(c) for c in rows[0]]
    body = [[to_text(c) for c in r] for r in rows[1:]]
    return check_rows(columns, body)



@router.get("/batches/{batch_id}/clean")
def get_batch_clean(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    """Layer bersih + karantina (read-only). Data asli tidak diubah."""
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")

    file_row = db.query(FileModel).filter(FileModel.batch_id == batch_id).first()
    if file_row is None:
        raise HTTPException(status_code=404, detail="Batch ini tidak punya file")

    try:
        data = get_file(file_row.storage_path)
    except Exception:
        raise HTTPException(status_code=502, detail="File mentah tidak bisa dibaca dari storage")

    rows = read_rows(data, file_row.filename)
    if not rows:
        raise HTTPException(status_code=422, detail="Format file tidak dikenali (harus .csv atau .xlsx)")

    to_text = lambda v: "" if v is None else str(v)
    columns = [to_text(c) for c in rows[0]]
    body = [[to_text(c) for c in r] for r in rows[1:]]
    return clean_rows(columns, body)
