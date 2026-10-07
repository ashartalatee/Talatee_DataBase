"""
Pintu masuk Eksperimen: setiap dataset yang menerima data otomatis punya
satu LabEntry (staging). Dari sana entri bisa dilanjutkan atau dipromosikan
jadi Project kalau sudah layak.

Aturan:
- Satu entri per DATASET, bukan per batch (upload file sama dua kali tidak
  menggandakan entri).
- Tidak dibuat kalau dataset itu sudah punya LabEntry atau sudah jadi Project.
- Hanya batch "success" yang memicu.
- Kegagalan di sini TIDAK BOLEH menggagalkan ingest (lihat safe_ensure_lab_entry).
"""
import logging

from sqlalchemy.orm import Session

from app.models import Batch, Business, Dataset, LabEntry, Project, Source

logger = logging.getLogger(__name__)


def ensure_lab_entry(
    db: Session, business: Business, source: Source, dataset: Dataset, batch: Batch
) -> LabEntry | None:
    if batch.status != "success":
        return None

    if db.query(LabEntry.id).filter(LabEntry.dataset_id == dataset.id).first():
        return None
    if db.query(Project.id).filter(Project.dataset_id == dataset.id).first():
        return None

    entry = LabEntry(
        name=f"Data masuk: {dataset.name}",
        note=(
            f"Masuk otomatis dari upload. Bisnis: {business.name} · "
            f"Sumber: {source.name} · {batch.records_saved} baris di batch pertama."
        ),
        business_id=business.id,
        dataset_id=dataset.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def safe_ensure_lab_entry(
    db: Session, business: Business, source: Source, dataset: Dataset, batch: Batch
) -> LabEntry | None:
    """Pembungkus aman: error apa pun hanya dicatat ke log, tidak dilempar."""
    try:
        return ensure_lab_entry(db, business, source, dataset, batch)
    except Exception:
        db.rollback()
        logger.exception("Gagal membuat entri Eksperimen untuk batch %s", batch.id)
        return None