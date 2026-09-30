import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kompas_idea import IDEA_STATUSES, KompasIdea
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(prefix="/kompas/ideas", tags=["kompas"], dependencies=[Depends(require_dashboard_session)])

MAX_IDEAS = 500


class IdeaIn(BaseModel):
    text: str = Field(min_length=1, max_length=280)


class IdeaPatch(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=280)
    status: str | None = None


class IdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    status: str
    created_at: datetime
    used_at: datetime | None = None


def _get_own(db: Session, idea_id: uuid.UUID, username: str) -> KompasIdea:
    idea = (
        db.query(KompasIdea)
        .filter(KompasIdea.id == idea_id, KompasIdea.username == username)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Ide tidak ditemukan")
    return idea


@router.get("", response_model=list[IdeaOut])
def list_ideas(username: str = Depends(require_dashboard_session), db: Session = Depends(get_db)):
    return (
        db.query(KompasIdea)
        .filter(KompasIdea.username == username)
        .order_by(KompasIdea.created_at.desc())
        .all()
    )


@router.post("", response_model=IdeaOut, status_code=201)
def create_idea(
    payload: IdeaIn,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Ide tidak boleh kosong")
    if db.query(KompasIdea).filter(KompasIdea.username == username).count() >= MAX_IDEAS:
        raise HTTPException(status_code=400, detail="Bank ide penuh, hapus beberapa dulu")
    idea = KompasIdea(username=username, text=text)
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


@router.patch("/{idea_id}", response_model=IdeaOut)
def update_idea(
    idea_id: uuid.UUID,
    payload: IdeaPatch,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    idea = _get_own(db, idea_id, username)
    data = payload.model_dump(exclude_unset=True)

    if data.get("text") is not None:
        text = data["text"].strip()
        if not text:
            raise HTTPException(status_code=400, detail="Ide tidak boleh kosong")
        idea.text = text
    if data.get("status") is not None:
        if data["status"] not in IDEA_STATUSES:
            raise HTTPException(status_code=400, detail="status tidak dikenal")
        idea.status = data["status"]
        idea.used_at = datetime.now(timezone.utc) if idea.status == "dipakai" else None

    db.commit()
    db.refresh(idea)
    return idea


@router.delete("/{idea_id}", status_code=204)
def delete_idea(
    idea_id: uuid.UUID,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    idea = _get_own(db, idea_id, username)
    db.delete(idea)
    db.commit()
