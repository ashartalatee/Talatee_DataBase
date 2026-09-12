from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi import File as FastAPIFile
from sqlalchemy.orm import Session

from app.connectors.file_upload import FileUploadConnector
from app.db.session import get_db
from app.ingestion.engine import IngestionEngine
from app.ingestion.mixed_channel import MixedChannelError, split_by_channel
from app.models.business import BUSINESS_CATEGORIES
from app.schemas.batch import BatchOut, MixedIngestResultItem
from app.security.api_key import require_api_key
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(prefix="/ingest", tags=["ingestion"])


async def _run_ingest(
    business_name: str,
    source_name: str,
    dataset_name: str,
    file: UploadFile,
    business_category: str,
    db: Session,
) -> BatchOut:
    """
    Logic inti upload -> ingest, dipakai bersama oleh route publik (dengan API
    key) dan route dashboard (tanpa API key). Jangan taruh logic baru
    langsung di route handler — taruh di sini supaya kedua jalur tetap identik.
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
    Endpoint PUBLIK untuk caller dari LUAR Talatee (misal Buku Kas Warung).
    Butuh header `Authorization: Bearer <api_key>` — lihat
    scripts/create_api_key.py untuk generate key baru.

    Selalu return 201 dengan objek Batch (baik status "success" maupun
    "failed") — kegagalan di dalam file (korup/kosong) TETAP tercatat sebagai
    batch, bukan HTTP error, supaya jejaknya bisa di-query lewat GET /batches.
    Hanya request yang secara fundamental tidak valid (misal ekstensi file
    tidak didukung, business_category bukan dari daftar yang diizinkan, atau
    API key tidak valid) yang mengembalikan error HTTP.
    """
    return await _run_ingest(business_name, source_name, dataset_name, file, business_category, db)


@router.post("/upload/dashboard", response_model=BatchOut, status_code=201)
async def ingest_upload_dashboard(
    business_name: str = Form(...),
    source_name: str = Form(...),
    dataset_name: str = Form(...),
    file: UploadFile = FastAPIFile(...),
    business_category: str = Form("lainnya"),
    db: Session = Depends(get_db),
    username: str = Depends(require_dashboard_session),
):
    """
    Endpoint khusus dashboard Talatee sendiri (halaman Upload). TIDAK pakai
    API key (beda trust boundary dari endpoint publik di atas), tapi TETAP
    butuh sesi login dashboard yang valid — konsisten dengan semua endpoint
    dashboard lain (datasets, core, projects, dst). Logic identik dengan
    /ingest/upload, lihat _run_ingest().
    """
    return await _run_ingest(business_name, source_name, dataset_name, file, business_category, db)


async def _run_mixed_ingest(
    business_name: str,
    dataset_name: str,
    file: UploadFile,
    business_category: str,
    db: Session,
) -> list[MixedIngestResultItem]:
    """
    Logic inti untuk mode "File ini campur beberapa channel" -- SATU file
    upload, tapi isinya beberapa channel sekaligus (dibedakan lewat kolom
    channel/platform/marketplace/sumber, lihat app/ingestion/
    mixed_channel.py). File di-split jadi N bagian per channel, lalu
    MASING-MASING lewat IngestionEngine.ingest() yang SAMA PERSIS dengan
    upload single-channel biasa -- jadi Source per channel otomatis
    ke-get-or-create, dan semua fitur lain (trash, channel_guard, dst) tetap
    berlaku tanpa perubahan sama sekali.

    TIDAK ADA source_name di sini -- itu justru intinya, source-nya
    ditentukan dari ISI file, bukan dipilih user.
    """
    if business_category not in BUSINESS_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"business_category harus salah satu dari: {', '.join(BUSINESS_CATEGORIES)}",
        )

    file_bytes = await file.read()

    try:
        channel_files = split_by_channel(file_bytes, file.filename)
    except MixedChannelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    base_name = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename

    engine = IngestionEngine(db)
    results: list[MixedIngestResultItem] = []
    for channel_name, csv_bytes in channel_files.items():
        synth_filename = f"{base_name}_{channel_name}.csv"
        try:
            connector = FileUploadConnector(
                source_name=channel_name,
                filename=synth_filename,
                file_bytes=csv_bytes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        batch = engine.ingest(
            connector,
            business_name=business_name,
            dataset_name=dataset_name,
            business_category=business_category,
        )
        results.append(
            MixedIngestResultItem(channel_name=channel_name, **BatchOut.model_validate(batch).model_dump())
        )

    return results


@router.post("/upload/mixed", response_model=list[MixedIngestResultItem], status_code=201)
async def ingest_upload_mixed(
    business_name: str = Form(..., description="Nama business/klien"),
    dataset_name: str = Form(..., description="Nama dataset, misal 'Transaksi Harian'"),
    file: UploadFile = FastAPIFile(..., description="File .csv atau .xlsx berisi kolom channel"),
    business_category: str = Form("lainnya"),
    db: Session = Depends(get_db),
    api_key=Depends(require_api_key),
):
    """
    Endpoint PUBLIK versi "campur channel" dari /ingest/upload -- satu file
    berisi data dari beberapa channel sekaligus (kolom channel/platform/
    marketplace/sumber WAJIB ada). Return list Batch, satu per channel yang
    ditemukan di file (bukan satu Batch tunggal seperti /ingest/upload).

    Kalau kolom channel tidak ada / ada baris tanpa nilai channel, seluruh
    request ditolak dengan HTTP 400 SEBELUM batch mana pun dibuat (beda dari
    /ingest/upload yang tetap mencatat batch "failed" untuk file
    korup/kosong -- di sini splitnya sendiri belum sempat menghasilkan
    apa-apa untuk dicatat).
    """
    return await _run_mixed_ingest(business_name, dataset_name, file, business_category, db)


@router.post("/upload/mixed/dashboard", response_model=list[MixedIngestResultItem], status_code=201)
async def ingest_upload_mixed_dashboard(
    business_name: str = Form(...),
    dataset_name: str = Form(...),
    file: UploadFile = FastAPIFile(...),
    business_category: str = Form("lainnya"),
    db: Session = Depends(get_db),
    username: str = Depends(require_dashboard_session),
):
    """Versi dashboard (sesi login, bukan API key) dari /ingest/upload/mixed."""
    return await _run_mixed_ingest(business_name, dataset_name, file, business_category, db)
