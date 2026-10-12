import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kompas_checkin import KompasCheckin
from app.models.kompas_journal import SEND_DELAY, KompasJournal
from app.security.dashboard_session import require_dashboard_session
from app.services.groq_stt import MAX_AUDIO_BYTES, MIN_AUDIO_BYTES, TranscribeError, transcribe

router = APIRouter(
    prefix="/kompas/journals", tags=["kompas"], dependencies=[Depends(require_dashboard_session)]
)

MIN_CHARS = 20
LIST_LIMIT = 30


class JournalIn(BaseModel):
    raw_transcript: str = Field(min_length=1, max_length=50000)
    text: str = Field(min_length=1, max_length=50000)
    day: date
    duration_seconds: int | None = Field(default=None, ge=0, le=7200)


class JournalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    day: date
    edited_text: str
    duration_seconds: int | None = None
    send_at: datetime
    status: str
    hooks: list[dict] | None = None
    error: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


@router.post("/transcribe")
def transcribe_audio(
    file: UploadFile = File(...),
    username: str = Depends(require_dashboard_session),
):
    """Audio masuk lewat memori, ditranskripsi, lalu dibuang. Tidak ada yang disimpan."""
    audio = file.file.read(MAX_AUDIO_BYTES + 1)
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Rekaman terlalu besar. Batasi sekitar 10 menit.")
    if len(audio) < MIN_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Rekaman terlalu pendek.")
    try:
        return {"text": transcribe(audio, file.content_type or "")}
    except TranscribeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("", response_model=list[JournalOut])
def list_journals(username: str = Depends(require_dashboard_session), db: Session = Depends(get_db)):
    return (
        db.query(KompasJournal)
        .filter(KompasJournal.username == username)
        .order_by(KompasJournal.created_at.desc())
        .limit(LIST_LIMIT)
        .all()
    )


@router.post("", response_model=JournalOut, status_code=201)
def create_journal(
    payload: JournalIn,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    body = payload.text.strip()
    if len(body) < MIN_CHARS:
        raise HTTPException(status_code=400, detail="Jurnal terlalu pendek, ceritakan sedikit lebih banyak.")
    if payload.day > date.today() + timedelta(days=1):
        raise HTTPException(status_code=400, detail="tanggal tidak boleh di masa depan")

    journal = KompasJournal(
        username=username,
        day=payload.day,
        raw_transcript=payload.raw_transcript.strip(),
        edited_text=body,
        duration_seconds=payload.duration_seconds,
        send_at=datetime.now(timezone.utc) + SEND_DELAY,
        status="pending",
    )
    db.add(journal)
    # Menyimpan jurnal = centang Speaking hari itu (pola sama dengan PUT /kompas/checkins).
    db.execute(
        insert(KompasCheckin)
        .values(id=uuid.uuid4(), username=username, habit="speaking", day=payload.day)
        .on_conflict_do_nothing(constraint="uq_kompas_checkin")
    )
    db.commit()
    db.refresh(journal)
    return journal


@router.delete("/{journal_id}", status_code=204)
def delete_journal(
    journal_id: uuid.UUID,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    j = (
        db.query(KompasJournal)
        .filter(KompasJournal.id == journal_id, KompasJournal.username == username)
        .first()
    )
    if j is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan")
    if j.status == "processing":
        raise HTTPException(status_code=409, detail="Jurnal sedang diproses, coba lagi sebentar.")
    db.delete(j)
    db.commit()
