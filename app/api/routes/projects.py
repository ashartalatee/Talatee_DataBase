import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch, Business, Dataset, LabEntry, Project, Source
from app.schemas.lab_entry import LabEntryOut
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(require_dashboard_session)])


def _to_out(project: Project, db: Session) -> ProjectOut:
    """Enrich dengan nama business & total records ASLI kalau project ini
    ditautkan ke business (bukan angka karangan)."""
    business_name = None
    business_total_records = None
    if project.business_id is not None:
        row = (
            db.query(
                Business.name,
                func.coalesce(func.sum(Batch.records_saved), 0),
            )
            .outerjoin(Source, Source.business_id == Business.id)
            .outerjoin(Dataset, Dataset.source_id == Source.id)
            .outerjoin(Batch, Batch.dataset_id == Dataset.id)
            .filter(Business.id == project.business_id)
            .group_by(Business.id)
            .first()
        )
        if row:
            business_name, business_total_records = row

    dataset_name = None
    if project.dataset_id is not None:
        dataset = db.get(Dataset, project.dataset_id)
        if dataset:
            dataset_name = dataset.name

    return ProjectOut(
        id=project.id,
        name=project.name,
        tier=project.tier,
        status_note=project.status_note,
        description=project.description,
        checklist=project.checklist,
        repo_url=project.repo_url,
        deploy_target=project.deploy_target,
        business_id=project.business_id,
        business_name=business_name,
        business_total_records=business_total_records,
        dataset_id=project.dataset_id,
        dataset_name=dataset_name,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.tier, Project.created_at).all()
    return [_to_out(p, db) for p in projects]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if payload.business_id is not None and db.get(Business, payload.business_id) is None:
        raise HTTPException(status_code=400, detail="business_id tidak ditemukan")
    if payload.dataset_id is not None and db.get(Dataset, payload.dataset_id) is None:
        raise HTTPException(status_code=400, detail="dataset_id tidak ditemukan")

    project = Project(
        name=payload.name,
        tier=payload.tier,
        status_note=payload.status_note,
        description=payload.description,
        checklist=[c.model_dump() for c in payload.checklist] if payload.checklist else None,
        repo_url=payload.repo_url,
        deploy_target=payload.deploy_target,
        business_id=payload.business_id,
        dataset_id=payload.dataset_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_out(project, db)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: uuid.UUID, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")

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
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return _to_out(project, db)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    db.delete(project)
    db.commit()


@router.post("/{project_id}/demote", response_model=LabEntryOut, status_code=201)
def demote_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Kebalikan dari POST /lab-entries/{id}/promote — kembalikan Project ini
    jadi catatan staging mentah di Talatee Laboratorium, termasuk tautan
    dataset-nya (kalau ada) supaya bisa dites ulang. Project-nya DIHAPUS
    dari registry setelah ini (bukan disimpan dobel).
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")

    entry = LabEntry(
        name=project.name,
        note=project.status_note,
        checklist=project.checklist,
        business_id=project.business_id,
        dataset_id=project.dataset_id,
    )
    db.add(entry)
    db.delete(project)
    db.commit()
    db.refresh(entry)

    from app.api.routes.lab_entries import _to_out as lab_entry_to_out

    return lab_entry_to_out(entry, db)
