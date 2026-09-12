from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch, Business, Dataset, DeletionLog, File as FileModel, Source
from app.schemas.trash import DeletionLogOut, TrashItemOut, TrashListOut

router = APIRouter(prefix="/trash", tags=["trash"], dependencies=[Depends(require_dashboard_session)])


@router.get("", response_model=TrashListOut)
def list_trash(db: Session = Depends(get_db)):
    """Semua item yang sedang di Sampah (hapus sesaat) — business, source,
    dataset, dan batch dicampur jadi satu daftar, diurutkan terbaru dulu.
    Ini murni baca (deleted_at IS NOT NULL di masing-masing tabel) — tidak
    menampilkan riwayat yang sudah dihapus PERMANEN, itu ada di
    GET /trash/log."""
    items: list[TrashItemOut] = []

    trashed_businesses = db.query(Business).filter(Business.deleted_at.isnot(None)).all()
    for b in trashed_businesses:
        items.append(
            TrashItemOut(
                level="business",
                id=b.id,
                name=b.name,
                context_path="",
                deleted_at=b.deleted_at,
                deleted_by=b.deleted_by,
            )
        )

    trashed_sources = (
        db.query(Source, Business.name)
        .outerjoin(Business, Source.business_id == Business.id)
        .filter(Source.deleted_at.isnot(None))
        .all()
    )
    for s, business_name in trashed_sources:
        items.append(
            TrashItemOut(
                level="source",
                id=s.id,
                name=s.name,
                context_path=business_name or "",
                deleted_at=s.deleted_at,
                deleted_by=s.deleted_by,
            )
        )

    trashed_datasets = (
        db.query(Dataset, Source.name, Business.name)
        .outerjoin(Source, Dataset.source_id == Source.id)
        .outerjoin(Business, Source.business_id == Business.id)
        .filter(Dataset.deleted_at.isnot(None))
        .all()
    )
    for d, source_name, business_name in trashed_datasets:
        context = " / ".join(p for p in [business_name, source_name] if p)
        items.append(
            TrashItemOut(
                level="dataset",
                id=d.id,
                name=d.name,
                context_path=context,
                deleted_at=d.deleted_at,
                deleted_by=d.deleted_by,
            )
        )

    trashed_batches = (
        db.query(Batch, Dataset.name, Source.name, Business.name, FileModel.filename)
        .outerjoin(Dataset, Batch.dataset_id == Dataset.id)
        .outerjoin(Source, Dataset.source_id == Source.id)
        .outerjoin(Business, Source.business_id == Business.id)
        .outerjoin(FileModel, FileModel.batch_id == Batch.id)
        .filter(Batch.deleted_at.isnot(None))
        .all()
    )
    for b, dataset_name, source_name, business_name, filename in trashed_batches:
        context = " / ".join(p for p in [business_name, source_name, dataset_name] if p)
        # PENTING: nama di sini harus SAMA PERSIS dengan salah satu nilai di
        # expected_names pada POST .../permanent (app/api/routes/batches.py)
        # — itu yang dipakai sebagai teks konfirmasi "ketik ulang nama" di
        # dashboard, jadi kalau beda user tidak akan pernah bisa konfirmasi.
        items.append(
            TrashItemOut(
                level="batch",
                id=b.id,
                name=filename or f"Batch {b.started_at:%Y-%m-%d %H:%M} ({b.status})",
                context_path=context,
                deleted_at=b.deleted_at,
                deleted_by=b.deleted_by,
            )
        )

    items.sort(key=lambda i: i.deleted_at, reverse=True)
    return TrashListOut(items=items)


@router.get("/log", response_model=list[DeletionLogOut])
def list_deletion_log(db: Session = Depends(get_db)):
    """Riwayat HAPUS PERMANEN — data aslinya sudah tidak ada, ini cuma
    jejak "apa yang pernah dihapus, siapa, kapan" (lihat app/models/
    deletion_log.py). Selalu ada, tidak pernah kosong-tanpa-jejak untuk
    aksi yang memang sudah dieksekusi."""
    return (
        db.query(DeletionLog)
        .order_by(DeletionLog.deleted_at.desc())
        .limit(200)
        .all()
    )
