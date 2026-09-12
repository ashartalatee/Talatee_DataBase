"""
Endpoint untuk 3 gap Data Trust Spec yang sebelumnya masih terbuka
(lihat PROJECT_CONTEXT_TALATEE.md bagian 7, sekarang dipindah ke 6e/6f/6g):

- Correction Model (spec section 14) -- koreksi manual 1 field di 1 baris,
  dengan history lengkap, tanpa merusak RAW immutability.
- Reconciliation (spec section 16) -- banding total dari luar Talatee vs
  hasil hitung Talatee sendiri.
- Data Passport (spec section 6) -- 1 endpoint yang merangkum "dari mana
  data ini, sudah divalidasi apa belum, apa yang pernah dikoreksi, apakah
  pernah direkonsiliasi" -- supaya dashboard bisa jawab pertanyaan itu tanpa
  user harus buka banyak tempat.
"""
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import (
    Batch,
    Correction,
    CORRECTABLE_FIELDS,
    CoreTransaction,
    Dataset,
    File,
    Reconciliation,
)
from app.api.routes.core import _compute_quality
from app.services import trash as trash_service

router = APIRouter(prefix="/datasets", tags=["data-trust"], dependencies=[Depends(require_dashboard_session)])


# ============================================================
# CORRECTION MODEL — spec section 14
# ============================================================

class CorrectionRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    field_name: str
    corrected_value: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    corrected_by: str | None = None


@router.post("/{dataset_id}/corrections")
def create_correction(dataset_id: uuid.UUID, body: CorrectionRequest, db: Session = Depends(get_db)):
    """
    Ajukan koreksi manual untuk 1 field di 1 order_id. TIDAK langsung
    mengubah core_transactions -- correction baru berlaku setelah "Bersihkan
    Data" (POST /datasets/{id}/process) dijalankan ulang, karena
    core_processor.py yang menerapkannya (lihat _load_active_corrections &
    _cast_correction_value di sana). Ini konsisten dengan Rule 03 (never
    silently modify data) -- perubahan HANYA lewat jalur processing yang
    sama untuk semua baris, bukan UPDATE langsung ke 1 baris di tengah.

    original_value diisi otomatis dari nilai TERKINI di core_transactions
    (kalau baris itu ada) -- murni untuk riwayat/audit, tidak memengaruhi
    logika penerapan correction.
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    if body.field_name not in CORRECTABLE_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"field_name '{body.field_name}' tidak boleh dikoreksi. "
            f"Field yang boleh: {sorted(CORRECTABLE_FIELDS)}",
        )

    existing_row = (
        db.query(CoreTransaction)
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.order_id == body.order_id)
        .first()
    )
    original_value = str(getattr(existing_row, body.field_name)) if existing_row is not None else None

    prior_version = (
        db.query(func.max(Correction.correction_version))
        .filter(
            Correction.dataset_id == dataset_id,
            Correction.order_id == body.order_id,
            Correction.field_name == body.field_name,
        )
        .scalar()
    )
    next_version = (prior_version or 0) + 1

    correction = Correction(
        dataset_id=dataset_id,
        order_id=body.order_id,
        field_name=body.field_name,
        original_value=original_value,
        corrected_value=body.corrected_value,
        reason=body.reason,
        corrected_by=body.corrected_by,
        correction_version=next_version,
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)

    return {
        "id": str(correction.id),
        "order_id": correction.order_id,
        "field_name": correction.field_name,
        "original_value": correction.original_value,
        "corrected_value": correction.corrected_value,
        "correction_version": correction.correction_version,
        "note": (
            "Correction tersimpan, tapi BELUM diterapkan ke data. Jalankan "
            "'Bersihkan Data' lagi supaya nilai baru dipakai."
        ),
    }


@router.get("/{dataset_id}/corrections")
def list_corrections(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """Riwayat LENGKAP semua correction (bukan cuma yang aktif) -- urut
    terbaru dulu, untuk keperluan audit trail (Rule 05: traceable)."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    rows = (
        db.query(Correction)
        .filter(Correction.dataset_id == dataset_id)
        .order_by(Correction.corrected_at.desc())
        .all()
    )
    return [
        {
            "id": str(c.id),
            "order_id": c.order_id,
            "field_name": c.field_name,
            "original_value": c.original_value,
            "corrected_value": c.corrected_value,
            "reason": c.reason,
            "corrected_by": c.corrected_by,
            "correction_version": c.correction_version,
            "corrected_at": c.corrected_at.isoformat() if c.corrected_at else None,
        }
        for c in rows
    ]


# ============================================================
# RECONCILIATION — spec section 16
# ============================================================

class ReconciliationRequest(BaseModel):
    period_label: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Format YYYY-MM, mis. '2026-01'")
    source_total: Decimal
    notes: str | None = None
    tolerance: Decimal = Field(default=Decimal("1.00"), ge=0, description="Toleransi selisih (rupiah) sebelum dianggap FAILED")


@router.post("/{dataset_id}/reconciliation")
def run_reconciliation(dataset_id: uuid.UUID, body: ReconciliationRequest, db: Session = Depends(get_db)):
    """
    Banding source_total (angka dari LUAR Talatee, mis. dashboard
    marketplace asli) vs talatee_total (SUM subtotal dari core_transactions
    yang is_revenue=True, untuk bulan period_label). Hasilnya disimpan
    sebagai baris baru (append-only, bukan update) -- riwayat pengecekan
    tetap ada meski dataset diproses ulang nanti.

    Ini pengecekan TERPISAH dari trust_status -- reconciliation FAILED
    TIDAK otomatis menurunkan trust_status dataset (spec tidak mewajibkan
    itu, dan tidak semua dataset akan pernah punya angka pembanding dari
    luar), tapi hasilnya tercatat untuk dilihat manual.
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    try:
        year, month = (int(p) for p in body.period_label.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="period_label harus format YYYY-MM")

    talatee_total = (
        db.query(func.coalesce(func.sum(CoreTransaction.subtotal), 0))
        .filter(
            CoreTransaction.dataset_id == dataset_id,
            CoreTransaction.is_revenue.is_(True),
            func.extract("year", CoreTransaction.transaction_date) == year,
            func.extract("month", CoreTransaction.transaction_date) == month,
        )
        .scalar()
    )
    talatee_total = Decimal(talatee_total)
    difference = body.source_total - talatee_total
    status = "PASSED" if abs(difference) <= body.tolerance else "FAILED"

    reconciliation = Reconciliation(
        dataset_id=dataset_id,
        period_label=body.period_label,
        source_total=body.source_total,
        talatee_total=talatee_total,
        difference=difference,
        status=status,
        notes=body.notes,
    )
    db.add(reconciliation)
    db.commit()
    db.refresh(reconciliation)

    return {
        "id": str(reconciliation.id),
        "period_label": reconciliation.period_label,
        "source_total": str(reconciliation.source_total),
        "talatee_total": str(reconciliation.talatee_total),
        "difference": str(reconciliation.difference),
        "status": reconciliation.status,
        "hint": (
            None
            if status == "PASSED"
            else (
                "Selisih di luar toleransi. Penyebab umum (spec section 16): "
                "refund/cancellation yang belum masuk business rule, duplikat "
                "yang belum tertangkap, atau ada baris yang ke-filter/hilang "
                "saat processing. Cek scripts/investigate_duplicate_order_ids.py "
                "atau riwayat corrections untuk periode ini."
            )
        ),
    }


@router.get("/{dataset_id}/reconciliation")
def list_reconciliations(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    rows = (
        db.query(Reconciliation)
        .filter(Reconciliation.dataset_id == dataset_id)
        .order_by(Reconciliation.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(r.id),
            "period_label": r.period_label,
            "source_total": str(r.source_total),
            "talatee_total": str(r.talatee_total),
            "difference": str(r.difference),
            "status": r.status,
            "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ============================================================
# DATA PASSPORT — spec section 6
# ============================================================

@router.get("/{dataset_id}/passport")
def get_data_passport(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Satu endpoint yang jawab semua pertanyaan wajib dari spec section 1:
    "Angka ini dari mana? Sudah diperiksa belum? Apa yang berubah dari
    aslinya? Kenapa dianggap valid?" -- dengan MERANGKUM data yang sudah ada
    di tabel lain (datasets, batches, files, corrections, reconciliations,
    hasil _compute_quality), bukan tabel baru terpisah yang bisa
    tidak-sinkron dengan sumber aslinya.
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    batches = (
        db.query(Batch, File)
        .outerjoin(File, File.batch_id == Batch.id)
        .filter(Batch.dataset_id == dataset_id)
        .order_by(Batch.started_at)
        .all()
    )
    total_records = (
        db.query(func.count(CoreTransaction.id))
        .filter(CoreTransaction.dataset_id == dataset_id)
        .scalar()
    )

    quality = _compute_quality(db, dataset_id)

    correction_count = (
        db.query(func.count(Correction.id))
        .filter(Correction.dataset_id == dataset_id)
        .scalar()
    )
    latest_reconciliation = (
        db.query(Reconciliation)
        .filter(Reconciliation.dataset_id == dataset_id)
        .order_by(Reconciliation.created_at.desc())
        .first()
    )

    return {
        "dataset": {
            "id": str(dataset.id),
            "name": dataset.name,
            "description": dataset.description,
            "trust_status": dataset.trust_status,
            "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
            "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
        },
        "provenance": {
            "total_batches": len(batches),
            "total_raw_records": sum(b.records_saved or 0 for b, _f in batches),
            "sources": [
                {
                    "batch_id": str(b.id),
                    "filename": f.filename if f else None,
                    "uploaded_at": b.started_at.isoformat() if b.started_at else None,
                    "checksum": f.checksum if f else None,
                }
                for b, f in batches
            ],
        },
        "current_state": {
            "total_records_in_core": total_records,
            "quality_score": quality.get("quality_score"),
            "warnings": quality.get("warnings", []),
            "errors": quality.get("errors", []),
        },
        "corrections": {
            "total_applied_ever": correction_count,
        },
        "reconciliation": (
            None
            if latest_reconciliation is None
            else {
                "period_label": latest_reconciliation.period_label,
                "status": latest_reconciliation.status,
                "difference": str(latest_reconciliation.difference),
                "checked_at": latest_reconciliation.created_at.isoformat()
                if latest_reconciliation.created_at
                else None,
            }
        ),
    }
