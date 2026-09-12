"""
Layer "Trash" (hapus sesaat) & "Purge" (hapus permanen) untuk Business,
Source, Dataset, dan Batch. Ditaruh di satu file (bukan tersebar di
masing-masing route) supaya perilaku cascade & aturan visibilitas konsisten
di keempat level, dan tidak ada implementasi berbeda yang bisa saling
melenceng.

ATURAN VISIBILITAS (dipakai di semua query list/detail/stats/insights):
sebuah baris kelihatan HANYA kalau dirinya SENDIRI dan SEMUA leluhurnya
(Business -> Source -> Dataset -> Batch) tidak di-trash. Trash TIDAK
menulis deleted_at ke anak saat parent di-trash (supaya restore anak yang
independen tetap butuh parent-nya juga direstore, dan restore parent tidak
"menghidupkan" anak yang sengaja dihapus sendiri sebelumnya) — makanya
visibilitas selalu dicek berantai lewat helper di bawah, bukan cukup baca
1 kolom.

PURGE (hapus permanen) kebalikannya: SELALU cascade nyata ke semua anak,
apa pun status trash mereka masing-masing — karena baris yang mau dihapus
levelnya lebih tinggi tidak boleh menyisakan anak yatim (foreign key orphan)
di DB, dan raw file-nya juga harus benar-benar hilang dari MinIO.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    Batch,
    Business,
    Correction,
    CoreTransaction,
    Dataset,
    DeletionLog,
    File as FileModel,
    Reconciliation,
    Source,
)
from app.models.connector import Connector
from app.models.lab_entry import LabEntry
from app.models.project import Project
from app.storage import minio_client


# ---------------------------------------------------------------------------
# Visibilitas
# ---------------------------------------------------------------------------

def visible_businesses_query(db: Session):
    return db.query(Business).filter(Business.deleted_at.is_(None))


def visible_sources_query(db: Session):
    """Query dasar Source yang benar-benar kelihatan (dirinya + business
    tidak di-trash). Selalu pakai ini (bukan db.query(Source) polos) untuk
    apa pun yang user-facing."""
    return (
        db.query(Source)
        .join(Business, Source.business_id == Business.id)
        .filter(Source.deleted_at.is_(None), Business.deleted_at.is_(None))
    )


def visible_datasets_query(db: Session):
    return (
        db.query(Dataset)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(
            Dataset.deleted_at.is_(None),
            Source.deleted_at.is_(None),
            Business.deleted_at.is_(None),
        )
    )


def visible_batches_query(db: Session):
    return (
        db.query(Batch)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(
            Batch.deleted_at.is_(None),
            Dataset.deleted_at.is_(None),
            Source.deleted_at.is_(None),
            Business.deleted_at.is_(None),
        )
    )


def is_source_visible(db: Session, source: Source) -> bool:
    if source.deleted_at is not None:
        return False
    business = db.get(Business, source.business_id)
    return business is not None and business.deleted_at is None


def is_dataset_visible(db: Session, dataset: Dataset) -> bool:
    if dataset.deleted_at is not None:
        return False
    source = db.get(Source, dataset.source_id)
    return source is not None and is_source_visible(db, source)


def is_batch_visible(db: Session, batch: Batch) -> bool:
    if batch.deleted_at is not None:
        return False
    dataset = db.get(Dataset, batch.dataset_id)
    return dataset is not None and is_dataset_visible(db, dataset)


# ---------------------------------------------------------------------------
# Trash / Restore (hapus sesaat)
# ---------------------------------------------------------------------------

def trash_business(db: Session, business: Business, deleted_by: str | None) -> None:
    business.deleted_at = datetime.now(timezone.utc)
    business.deleted_by = deleted_by
    db.commit()


def restore_business(db: Session, business: Business) -> None:
    business.deleted_at = None
    business.deleted_by = None
    db.commit()


def trash_source(db: Session, source: Source, deleted_by: str | None) -> None:
    source.deleted_at = datetime.now(timezone.utc)
    source.deleted_by = deleted_by
    db.commit()


def restore_source(db: Session, source: Source) -> None:
    source.deleted_at = None
    source.deleted_by = None
    db.commit()


def trash_dataset(db: Session, dataset: Dataset, deleted_by: str | None) -> None:
    dataset.deleted_at = datetime.now(timezone.utc)
    dataset.deleted_by = deleted_by
    db.commit()


def restore_dataset(db: Session, dataset: Dataset) -> None:
    dataset.deleted_at = None
    dataset.deleted_by = None
    db.commit()


def trash_batch(db: Session, batch: Batch, deleted_by: str | None) -> None:
    batch.deleted_at = datetime.now(timezone.utc)
    batch.deleted_by = deleted_by
    db.commit()
    _reprocess_dataset_best_effort(db, batch.dataset_id)


def restore_batch(db: Session, batch: Batch) -> None:
    batch.deleted_at = None
    batch.deleted_by = None
    db.commit()
    _reprocess_dataset_best_effort(db, batch.dataset_id)


def _reprocess_dataset_best_effort(db: Session, dataset_id: uuid.UUID) -> None:
    """Trigger ulang Raw->Core (lihat core_processor.process_dataset) supaya
    core_transactions langsung mencerminkan batch yang baru saja di-trash/
    di-restore, TANPA user harus klik "Process Data" manual lagi. Dibungkus
    try/except supaya aksi trash/restore-nya sendiri (yang sudah ter-commit
    di atas) tidak gagal cuma karena reprocess bermasalah — kalau reprocess
    gagal, dataset otomatis balik ke jalur normal "belum diproses ulang",
    user masih bisa klik Process Data manual dari dashboard."""
    try:
        from app.ingestion.core_processor import process_dataset

        process_dataset(db, dataset_id)
    except Exception:
        db.rollback()


# ---------------------------------------------------------------------------
# Purge (hapus permanen) — selalu cascade nyata, tulis DeletionLog dulu
# sebelum data hilang.
# ---------------------------------------------------------------------------

def _delete_batches_fully(db: Session, batch_ids: list[uuid.UUID]) -> tuple[int, int, int]:
    """Hapus permanen files (+ objek MinIO-nya) dan core_transactions milik
    sekumpulan batch, lalu baris batch itu sendiri. TIDAK menghapus
    connectors/dataset/source/business — itu tanggung jawab pemanggil.
    Return (files_deleted, records_deleted, batches_deleted)."""
    if not batch_ids:
        return 0, 0, 0

    files = db.query(FileModel).filter(FileModel.batch_id.in_(batch_ids)).all()
    for f in files:
        try:
            minio_client.delete_file(f.storage_path)
        except Exception:
            # Best-effort: kalau objeknya sudah tidak ada / MinIO unreachable,
            # tetap lanjutkan hapus baris DB-nya — jangan biarkan hapus
            # permanen macet cuma gara-gara satu object storage.
            pass
    files_deleted = len(files)

    records_deleted = (
        db.query(CoreTransaction)
        .filter(CoreTransaction.batch_id.in_(batch_ids))
        .delete(synchronize_session=False)
    )
    db.query(FileModel).filter(FileModel.batch_id.in_(batch_ids)).delete(synchronize_session=False)
    batches_deleted = (
        db.query(Batch).filter(Batch.id.in_(batch_ids)).delete(synchronize_session=False)
    )
    return files_deleted, records_deleted, batches_deleted


def _delete_datasets_fully(db: Session, dataset_ids: list[uuid.UUID]) -> tuple[int, int, int]:
    """Hapus permanen semua batch (lewat _delete_batches_fully) + correction
    + reconciliation milik sekumpulan dataset, lalu baris dataset itu
    sendiri. TIDAK menghapus source/connector/business. Return
    (files_deleted, records_deleted, batches_deleted)."""
    if not dataset_ids:
        return 0, 0, 0

    batch_ids = [b.id for b in db.query(Batch.id).filter(Batch.dataset_id.in_(dataset_ids)).all()]
    files_deleted, records_deleted, batches_deleted = _delete_batches_fully(db, batch_ids)

    db.query(Correction).filter(Correction.dataset_id.in_(dataset_ids)).delete(synchronize_session=False)
    db.query(Reconciliation).filter(Reconciliation.dataset_id.in_(dataset_ids)).delete(synchronize_session=False)
    # LabEntry.dataset_id itu referensi OPSIONAL (catatan eksperimen berdiri
    # sendiri, bukan anak dari Dataset) -- dikosongkan, bukan ikut dihapus
    # notenya, supaya menghapus dataset tidak diam-diam menghapus catatan
    # laboratorium orang.
    db.query(LabEntry).filter(LabEntry.dataset_id.in_(dataset_ids)).update(
        {"dataset_id": None}, synchronize_session=False
    )
    db.query(Project).filter(Project.dataset_id.in_(dataset_ids)).update(
        {"dataset_id": None}, synchronize_session=False
    )
    db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).delete(synchronize_session=False)
    return files_deleted, records_deleted, batches_deleted


def purge_batch(db: Session, batch: Batch, deleted_by: str | None, reason: str | None = None) -> DeletionLog:
    dataset = db.get(Dataset, batch.dataset_id)
    source = db.get(Source, dataset.source_id) if dataset else None
    context_path = " / ".join(
        p for p in [source.name if source else None, dataset.name if dataset else None] if p
    )
    files_deleted, records_deleted, _ = _delete_batches_fully(db, [batch.id])

    log = DeletionLog(
        level="batch",
        entity_id=batch.id,
        entity_name=f"Batch {batch.started_at:%Y-%m-%d %H:%M} ({batch.status})",
        context_path=context_path,
        batches_deleted=1,
        files_deleted=files_deleted,
        records_deleted=records_deleted,
        reason=reason,
        deleted_by=deleted_by,
    )
    db.add(log)
    db.commit()

    if dataset is not None:
        _reprocess_dataset_best_effort(db, dataset.id)
    return log


def purge_dataset(db: Session, dataset: Dataset, deleted_by: str | None, reason: str | None = None) -> DeletionLog:
    source = db.get(Source, dataset.source_id)
    files_deleted, records_deleted, batches_deleted = _delete_datasets_fully(db, [dataset.id])

    log = DeletionLog(
        level="dataset",
        entity_id=dataset.id,
        entity_name=dataset.name,
        context_path=source.name if source else "",
        batches_deleted=batches_deleted,
        files_deleted=files_deleted,
        records_deleted=records_deleted,
        reason=reason,
        deleted_by=deleted_by,
    )
    db.add(log)
    db.commit()
    return log


def purge_source(db: Session, source: Source, deleted_by: str | None, reason: str | None = None) -> DeletionLog:
    dataset_ids = [d.id for d in db.query(Dataset.id).filter(Dataset.source_id == source.id).all()]
    files_deleted, records_deleted, batches_deleted = _delete_datasets_fully(db, dataset_ids)

    # Connectors baru boleh dihapus SETELAH semua batch di bawah source ini
    # hilang (batches.connector_id FK ke connectors, nullable=False).
    db.query(Connector).filter(Connector.source_id == source.id).delete(synchronize_session=False)

    source_name = source.name
    source_id = source.id
    db.delete(source)  # ORM delete -- aman, datasets/connectors sudah lebih dulu dihapus manual di atas
    db.commit()

    log = DeletionLog(
        level="source",
        entity_id=source_id,
        entity_name=source_name,
        context_path="",
        batches_deleted=batches_deleted,
        files_deleted=files_deleted,
        records_deleted=records_deleted,
        reason=reason,
        deleted_by=deleted_by,
    )
    db.add(log)
    db.commit()
    return log


def purge_business(db: Session, business: Business, deleted_by: str | None, reason: str | None = None) -> DeletionLog:
    """Hapus permanen SATU business beserta SEMUA source/dataset/batch/file/
    core_transactions/correction/reconciliation/connector di bawahnya.
    Ini level paling atas -- tidak ada yang lebih tinggi untuk dicek."""
    source_ids = [s.id for s in db.query(Source.id).filter(Source.business_id == business.id).all()]
    dataset_ids = [
        d.id for d in db.query(Dataset.id).filter(Dataset.source_id.in_(source_ids)).all()
    ] if source_ids else []

    files_deleted, records_deleted, batches_deleted = _delete_datasets_fully(db, dataset_ids)

    if source_ids:
        db.query(Connector).filter(Connector.source_id.in_(source_ids)).delete(synchronize_session=False)
        db.query(Source).filter(Source.id.in_(source_ids)).delete(synchronize_session=False)

    # LabEntry.business_id itu referensi OPSIONAL juga (lihat catatan di
    # _delete_datasets_fully) -- dikosongkan, bukan ikut dihapus notenya.
    db.query(LabEntry).filter(LabEntry.business_id == business.id).update(
        {"business_id": None}, synchronize_session=False
    )
    db.query(Project).filter(Project.business_id == business.id).update(
        {"business_id": None}, synchronize_session=False
    )

    business_name = business.name
    business_id = business.id
    db.delete(business)  # ORM delete -- aman, sources/datasets/batches/connectors sudah dihapus manual
    db.commit()

    log = DeletionLog(
        level="business",
        entity_id=business_id,
        entity_name=business_name,
        context_path="",
        batches_deleted=batches_deleted,
        files_deleted=files_deleted,
        records_deleted=records_deleted,
        reason=reason,
        deleted_by=deleted_by,
    )
    db.add(log)
    db.commit()
    return log
