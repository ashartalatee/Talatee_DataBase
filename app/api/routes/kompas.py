import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kompas_checkin import KOMPAS_HABITS, KompasCheckin
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(prefix="/kompas", tags=["kompas"], dependencies=[Depends(require_dashboard_session)])


class CheckinIn(BaseModel):
    habit: str
    day: date
    done: bool


class ImportIn(BaseModel):
    log: dict[str, list[date]]


def _latest_allowed_day() -> date:
    # +1 hari supaya beda zona waktu antara browser dan server tidak menolak "hari ini".
    return date.today() + timedelta(days=1)


@router.get("/checkins", response_model=dict[str, list[date]])
def list_checkins(
    days: int = Query(400, ge=1, le=1000),
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(KompasCheckin.habit, KompasCheckin.day)
        .filter(KompasCheckin.username == username, KompasCheckin.day >= since)
        .order_by(KompasCheckin.day)
        .all()
    )
    out: dict[str, list[date]] = {h: [] for h in KOMPAS_HABITS}
    for habit, day in rows:
        out.setdefault(habit, []).append(day)
    return out


@router.put("/checkins", response_model=CheckinIn)
def set_checkin(
    payload: CheckinIn,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    if payload.habit not in KOMPAS_HABITS:
        raise HTTPException(status_code=400, detail="habit tidak dikenal")
    if payload.day > _latest_allowed_day():
        raise HTTPException(status_code=400, detail="tanggal tidak boleh di masa depan")

    if payload.done:
        db.execute(
            insert(KompasCheckin)
            .values(id=uuid.uuid4(), username=username, habit=payload.habit, day=payload.day)
            .on_conflict_do_nothing(constraint="uq_kompas_checkin")
        )
    else:
        (
            db.query(KompasCheckin)
            .filter(
                KompasCheckin.username == username,
                KompasCheckin.habit == payload.habit,
                KompasCheckin.day == payload.day,
            )
            .delete(synchronize_session=False)
        )
    db.commit()
    return payload


@router.post("/import")
def import_checkins(
    payload: ImportIn,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    """Pindahkan centang lama dari browser ke database, sekali saja.
    Aman dipanggil ulang: baris yang sudah ada dilewati."""
    limit = _latest_allowed_day()
    rows = [
        {"id": uuid.uuid4(), "username": username, "habit": habit, "day": d}
        for habit, days in payload.log.items()
        if habit in KOMPAS_HABITS
        for d in set(days)
        if d <= limit
    ][:3000]
    if rows:
        db.execute(
            insert(KompasCheckin).on_conflict_do_nothing(constraint="uq_kompas_checkin"),
            rows,
        )
    db.commit()
    return {"imported": len(rows)}
