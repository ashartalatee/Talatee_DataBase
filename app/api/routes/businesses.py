import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Batch, Business, Dataset, Source
from app.models.business import BUSINESS_CATEGORIES
from app.schemas.business import BusinessListItemOut, BusinessOut
from app.schemas.source import SourceOut

router = APIRouter(prefix="/businesses", tags=["businesses"], dependencies=[Depends(require_dashboard_session)])


@router.get("/categories", response_model=list[str])
def list_business_categories():
    """Daftar tetap kategori business (dropdown) — dipakai UI, bukan free text."""
    return BUSINESS_CATEGORIES


@router.get("", response_model=list[BusinessListItemOut])
def list_businesses(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Business,
            func.count(func.distinct(Source.id)),
            func.count(func.distinct(Dataset.id)),
            func.coalesce(func.sum(Batch.records_saved), 0),
        )
        .outerjoin(Source, Source.business_id == Business.id)
        .outerjoin(Dataset, Dataset.source_id == Source.id)
        .outerjoin(Batch, Batch.dataset_id == Dataset.id)
        .group_by(Business.id)
        .order_by(Business.created_at.desc())
        .all()
    )
    return [
        BusinessListItemOut(
            id=b.id,
            name=b.name,
            category=b.category,
            status=b.status,
            created_at=b.created_at,
            total_sources=total_sources,
            total_datasets=total_datasets,
            total_records=total_records,
        )
        for b, total_sources, total_datasets, total_records in rows
    ]


@router.get("/{business_id}", response_model=BusinessOut)
def get_business(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business tidak ditemukan")
    return business


@router.get("/{business_id}/sources", response_model=list[SourceOut])
def list_business_sources(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business tidak ditemukan")
    return db.query(Source).filter(Source.business_id == business_id).all()
