import uuid
from datetime import date, datetime, timezone
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kompas_reading import DAILY_LIMIT, KompasReading
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(prefix="/kompas/reading", tags=["kompas"], dependencies=[Depends(require_dashboard_session)])

MAX_SAVED = 300
VIDEO_HOSTS = ("youtube.com", "youtu.be", "tiktok.com", "vimeo.com")


class ReadingIn(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    title: str | None = Field(default=None, max_length=200)


class ReadingPatch(BaseModel):
    action: Literal["today", "unplan", "read", "unread"]
    day: date | None = None


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    title: str
    kind: str
    created_at: datetime
    planned_for: date | None = None
    read_at: datetime | None = None


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _get_own(db: Session, item_id: uuid.UUID, username: str) -> KompasReading:
    item = (
        db.query(KompasReading)
        .filter(KompasReading.id == item_id, KompasReading.username == username)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Bacaan tidak ditemukan")
    return item


@router.get("", response_model=list[ReadingOut])
def list_reading(username: str = Depends(require_dashboard_session), db: Session = Depends(get_db)):
    return (
        db.query(KompasReading)
        .filter(KompasReading.username == username)
        .order_by(KompasReading.created_at.desc())
        .all()
    )


@router.post("", response_model=ReadingOut, status_code=201)
def create_reading(
    payload: ReadingIn,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    url = payload.url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Tautan harus diawali http:// atau https://")

    if db.query(KompasReading).filter(KompasReading.username == username).count() >= MAX_SAVED:
        raise HTTPException(status_code=400, detail="Simpanan penuh, hapus beberapa dulu")
    exists = (
        db.query(KompasReading.id)
        .filter(KompasReading.username == username, KompasReading.url == url)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Tautan ini sudah tersimpan")

    host = _host(url)
    item = KompasReading(
        username=username,
        url=url,
        title=(payload.title or "").strip() or host,
        kind="video" if host.endswith(VIDEO_HOSTS) else "artikel",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ReadingOut)
def act_reading(
    item_id: uuid.UUID,
    payload: ReadingPatch,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    item = _get_own(db, item_id, username)

    if payload.action == "today":
        if payload.day is None:
            raise HTTPException(status_code=400, detail="day wajib diisi")
        # Toleransi 1 hari untuk beda zona waktu antara browser dan server.
        if abs((payload.day - date.today()).days) > 1:
            raise HTTPException(status_code=400, detail="Tanggal tidak valid")
        if item.planned_for != payload.day:
            taken = (
                db.query(KompasReading)
                .filter(
                    KompasReading.username == username,
                    KompasReading.planned_for == payload.day,
                    KompasReading.id != item.id,
                )
                .count()
            )
            if taken >= DAILY_LIMIT:
                raise HTTPException(status_code=400, detail=f"Sudah {DAILY_LIMIT} bacaan untuk hari ini")
            item.planned_for = payload.day
    elif payload.action == "unplan":
        item.planned_for = None
    elif payload.action == "read":
        item.read_at = datetime.now(timezone.utc)
    else:  # unread
        item.read_at = None

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_reading(
    item_id: uuid.UUID,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    item = _get_own(db, item_id, username)
    db.delete(item)
    db.commit()
