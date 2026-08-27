from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi import File as FastAPIFile
from sqlalchemy.orm import Session

from app.connectors.file_upload import FileUploadConnector
from app.db.session import get_db
from app.ingestion.engine import IngestionEngine
from app.models.business import BUSINESS_CATEGORIES
from app.schemas.batch import BatchOut
from app.security.api_key import require_api_key

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/upload", response_model=BatchOut, status_code=201)
async def ingest_upload(
    business_name: str = Form(..., description="Nama business/klien, misal 'Resto Padang Jaya'"),
    source_name: str = Form(..., description="Nama source, misal 'Toko Kelontong'"),
    dataset_name: str = Form(..., description="Nama dataset, misal 'Orders'"),
    file: UploadFile = FastAPIFile(..., description="File .csv atau .xlsx"),
    business_category: str = Form(
        "lainnya",
        description=f"Kategori business, salah satu dari: {', '.join(BUSINESS_CATEGORIES)}. "
        "Hanya dipakai kalau business BARU dibuat — diabaikan kalau business sudah ada.",
    ),
    db: Session = Depends(get_db),
    api_key=Depends(require_api_key),
):
    """
    Trigger pipeline ingest penuh lewat FileUploadConnector: auto-create
    business/source/connector/dataset kalau belum ada -> validasi -> upload ke
    MinIO -> catat batch & file di Postgres.

    Butuh header `Authorization: Bearer <api_key>` — lihat scripts/create_api_key.py
    untuk generate key baru.

    Selalu return 201 dengan objek Batch (baik status "success" maupun
    "failed") — kegagalan di dalam file (korup/kosong) TETAP tercatat sebagai
    batch, bukan HTTP error, supaya jejaknya bisa di-query lewat GET /batches.
    Hanya request yang secara fundamental tidak valid (misal ekstensi file
    tidak didukung, business_category bukan dari daftar yang diizinkan, atau
    API key tidak valid) yang mengembalikan error HTTP.
    """
    if business_category not in BUSINESS_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"business_category harus salah satu dari: {', '.join(BUSINESS_CATEGORIES)}",
        )

    file_bytes = await file.read()

    try:
        connector = FileUploadConnector(
            source_name=source_name,
            filename=file.filename,
            file_bytes=file_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    engine = IngestionEngine(db)
    batch = engine.ingest(
        connector,
        business_name=business_name,
        dataset_name=dataset_name,
        business_category=business_category,
    )
    return batch
