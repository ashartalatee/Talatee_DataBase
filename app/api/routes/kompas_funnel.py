from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kompas_funnel import FUNNEL_STAGES, FUNNEL_STREAMS, MAX_COUNT, KompasFunnel
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(prefix="/kompas/funnel", tags=["kompas"], dependencies=[Depends(require_dashboard_session)])


class Bump(BaseModel):
    delta: Literal[-1, 1]


@router.get("")
def get_funnel(username: str = Depends(require_dashboard_session), db: Session = Depends(get_db)):
    """Semua angka sekaligus: {jalur: [tahap0, tahap1, tahap2, tahap3]}. Yang belum ada = 0."""
    data = {s: [0] * FUNNEL_STAGES for s in FUNNEL_STREAMS}
    rows = db.query(KompasFunnel).filter(KompasFunnel.username == username).all()
    for r in rows:
        if r.stream in data and 0 <= r.stage < FUNNEL_STAGES:
            data[r.stream][r.stage] = r.count
    return data


@router.post("/{stream}/{stage}")
def bump_funnel(
    stream: str,
    stage: int,
    payload: Bump,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    if stream not in FUNNEL_STREAMS:
        raise HTTPException(status_code=404, detail="Jalur tidak dikenal")
    if not 0 <= stage < FUNNEL_STAGES:
        raise HTTPException(status_code=404, detail="Tahap tidak dikenal")

    # Satu pernyataan atomik: dua klik cepat atau dua tab tidak saling menimpa,
    # dan angka tidak pernah di bawah 0 atau di atas MAX_COUNT.
    stmt = insert(KompasFunnel).values(
        username=username, stream=stream, stage=stage, count=max(payload.delta, 0)
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["username", "stream", "stage"],
        set_={
            "count": func.least(func.greatest(KompasFunnel.count + payload.delta, 0), MAX_COUNT),
            "updated_at": func.now(),
        },
    ).returning(KompasFunnel.count)
    value = db.execute(stmt).scalar_one()
    db.commit()
    return {"stream": stream, "stage": stage, "count": value}
