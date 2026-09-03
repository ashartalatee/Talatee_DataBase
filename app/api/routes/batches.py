import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch
from app.models import File as FileModel
from app.schemas.batch import BatchDetailOut, BatchOut, FileOut
from app.storage.minio_client import get_file

router = APIRouter(tags=["batches"], dependencies=[Depends(require_dashboard_session)])


@router.get("/batches", response_model=list[BatchOut])
def list_batches(
    dataset_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Batch)
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
