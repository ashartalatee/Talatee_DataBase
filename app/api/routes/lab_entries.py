import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Batch, Business, Dataset, LabEntry, Project, Source
from app.schemas.lab_entry import LabEntryCreate, LabEntryOut, LabEntryUpdate
from app.schemas.project import ProjectOut
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(
    prefix="/lab-entries",
    tags=["lab-entries"],
    dependencies=[Depends(require_dashboard_session)],
)


def _to_out(entry: LabEntry, db: Session) -> LabEntryOut:
    business_name = None
    business_total_records = None
    if entry.business_id is not None:
        row = (
            db.query(
                Business.name,
                func.coalesce(func.sum(Batch.records_saved), 0),
            )
            .outerjoin(Source, Source.business_id == Business.id)
            .outerjoin(Dataset, Dataset.source_id == Source.id)
            .outerjoin(Batch, Batch.dataset_id == Dataset.id)
            .filter(Business.id == entry.business_id)
            .group_by(Business.id)
            .first()
        )
        if row:
            business_name, business_total_records = row

    dataset_name = None
    if entry.dataset_id is not None:
        dataset = db.get(Dataset, entry.dataset_id)
        if dataset:
            dataset_name = dataset.name

    return LabEntryOut(
        id=entry.id,
        name=entry.name,
        note=entry.note,
        checklist=entry.checklist,
        business_id=entry.business_id,
        business_name=business_name,
        business_total_records=business_total_records,
        dataset_id=entry.dataset_id,
        dataset_name=dataset_name,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("", response_model=list[LabEntryOut])
def list_lab_entries(db: Session = Depends(get_db)):
    entries = db.query(LabEntry).order_by(LabEntry.created_at.desc()).all()
    return [_to_out(e, db) for e in entries]


@router.get("/{entry_id}", response_model=LabEntryOut)
def get_lab_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)):
    entry = db.get(LabEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entri tidak ditemukan")
    return _to_out(entry, db)


@router.post("", response_model=LabEntryOut, status_code=201)
def create_lab_entry(payload: LabEntryCreate, db: Session = Depends(get_db)):
    if payload.business_id is not None and db.get(Business, payload.business_id) is None:
        raise HTTPException(status_code=400, detail="business_id tidak ditemukan")
    if payload.dataset_id is not None and db.get(Dataset, payload.dataset_id) is None:
        raise HTTPException(status_code=400, detail="dataset_id tidak ditemukan")

    entry = LabEntry(
        name=payload.name,
        note=payload.note,
        checklist=[c.model_dump() for c in payload.checklist] if payload.checklist else None,
        business_id=payload.business_id,
        dataset_id=payload.dataset_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_out(entry, db)


@router.patch("/{entry_id}", response_model=LabEntryOut)
def update_lab_entry(entry_id: uuid.UUID, payload: LabEntryUpdate, db: Session = Depends(get_db)):
    entry = db.get(LabEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entri tidak ditemukan")

    data = payload.model_dump(exclude_unset=True)
    if "checklist" in data and data["checklist"] is not None:
        data["checklist"] = [c if isinstance(c, dict) else c.model_dump() for c in data["checklist"]]
    if "business_id" in data and data["business_id"] is not None:
        if db.get(Business, data["business_id"]) is None:
            raise HTTPException(status_code=400, detail="business_id tidak ditemukan")
    if "dataset_id" in data and data["dataset_id"] is not None:
        if db.get(Dataset, data["dataset_id"]) is None:
            raise HTTPException(status_code=400, detail="dataset_id tidak ditemukan")

    for field, value in data.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return _to_out(entry, db)


@router.delete("/{entry_id}", status_code=204)
def delete_lab_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)):
    entry = db.get(LabEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entri tidak ditemukan")
    db.delete(entry)
    db.commit()


@router.post("/{entry_id}/promote", response_model=ProjectOut, status_code=201)
def promote_lab_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Resmikan entri staging ini jadi Project beneran (tier=laboratorium),
    termasuk tautan dataset yang sudah ditest lewat pipeline (kalau ada).
    Setelah promote, entri staging-nya DIHAPUS.
    """
    entry = db.get(LabEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entri tidak ditemukan")

    project = Project(
        name=entry.name,
        tier="laboratorium",
        status_note=entry.note,
        checklist=entry.checklist,
        business_id=entry.business_id,
        dataset_id=entry.dataset_id,
    )
    db.add(project)
    db.delete(entry)
    db.commit()
    db.refresh(project)

    from app.api.routes.projects import _to_out as project_to_out

    return project_to_out(project, db)
