import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.models import Source
from app.schemas.source import SourceOut

router = APIRouter(prefix="/sources", tags=["sources"], dependencies=[Depends(require_dashboard_session)])


@router.get("", response_model=list[SourceOut])
def list_sources(business_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    query = db.query(Source)
    if business_id is not None:
        query = query.filter(Source.business_id == business_id)
    return query.order_by(Source.created_at.desc()).all()


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: uuid.UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source tidak ditemukan")
    return source
