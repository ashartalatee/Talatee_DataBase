import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kompas_parked import COOLDOWN_DAYS, KompasParked
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(prefix="/kompas/parked", tags=["kompas"], dependencies=[Depends(require_dashboard_session)])

MAX_PARKED = 300


class ParkedIn(BaseModel):
    text: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=280)


class ParkedPatch(BaseModel):
    status: str


class ParkedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    reason: str | None = None
    status: str
    created_at: datetime
    review_on: date
    decided_at: datetime | None = None


def _get_own(db: Session, item_id: uuid.UUID, username: str) -> KompasParked:
    item = (
        db.query(KompasParked)
        .filter(KompasParked.id == item_id, KompasParked.username == username)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Ide tidak ditemukan")
    return item


@router.get("", response_model=list[ParkedOut])
def list_parked(username: str = Depends(require_dashboard_session), db: Session = Depends(get_db)):
    return (
        db.query(KompasParked)
        .filter(KompasParked.username == username)
        .order_by(KompasParked.review_on, KompasParked.created_at)
        .all()
    )


@router.post("", response_model=ParkedOut, status_code=201)
def create_parked(
    payload: ParkedIn,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Ide tidak boleh kosong")
    if db.query(KompasParked).filter(KompasParked.username == username).count() >= MAX_PARKED:
        raise HTTPException(status_code=400, detail="Parkir penuh, lepas beberapa dulu")
    item = KompasParked(
        username=username,
        text=text,
        reason=(payload.reason or "").strip() or None,
        review_on=date.today() + timedelta(days=COOLDOWN_DAYS),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ParkedOut)
def decide_parked(
    item_id: uuid.UUID,
    payload: ParkedPatch,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    item = _get_own(db, item_id, username)

    if payload.status == "lolos":
        if item.status != "parkir":
            raise HTTPException(status_code=400, detail="Ide ini sudah ditinjau")
        # Masa tunggu ditegakkan di server. Toleransi +1 hari untuk beda zona waktu.
        if item.review_on > date.today() + timedelta(days=1):
            raise HTTPException(status_code=400, detail="Masa tunggu 30 hari belum selesai")
    elif payload.status == "eksperimen":
        if item.status != "lolos":
            raise HTTPException(status_code=400, detail="Ide harus lolos tinjauan dulu")
    else:
        raise HTTPException(status_code=400, detail="status tidak dikenal")

    item.status = payload.status
    item.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_parked(
    item_id: uuid.UUID,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    item = _get_own(db, item_id, username)
    db.delete(item)
    db.commit()
