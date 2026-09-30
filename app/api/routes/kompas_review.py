from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kompas_review import KompasReview
from app.security.dashboard_session import require_dashboard_session

router = APIRouter(prefix="/kompas/reviews", tags=["kompas"], dependencies=[Depends(require_dashboard_session)])

MAX_WEEKS_BACK = 120  # hari


class ReviewIn(BaseModel):
    built: str = Field(default="", max_length=1000)
    improve: str = Field(default="", max_length=1000)
    proud: str = Field(default="", max_length=1000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    week_start: date
    built: str
    improve: str
    proud: str
    updated_at: datetime


@router.get("", response_model=list[ReviewOut])
def list_reviews(username: str = Depends(require_dashboard_session), db: Session = Depends(get_db)):
    return (
        db.query(KompasReview)
        .filter(KompasReview.username == username)
        .order_by(KompasReview.week_start.desc())
        .limit(104)
        .all()
    )


@router.put("/{week_start}", response_model=ReviewOut)
def save_review(
    week_start: date,
    payload: ReviewIn,
    username: str = Depends(require_dashboard_session),
    db: Session = Depends(get_db),
):
    if week_start.weekday() != 0:
        raise HTTPException(status_code=400, detail="week_start harus hari Senin")
    today = date.today()
    # Toleransi +1 hari untuk beda zona waktu; tidak boleh review minggu depan.
    if week_start > today + timedelta(days=1):
        raise HTTPException(status_code=400, detail="Tidak bisa mereview minggu yang belum datang")
    if week_start < today - timedelta(days=MAX_WEEKS_BACK):
        raise HTTPException(status_code=400, detail="Minggu terlalu lama")

    built, improve, proud = payload.built.strip(), payload.improve.strip(), payload.proud.strip()
    if not (built or improve or proud):
        raise HTTPException(status_code=400, detail="Isi minimal satu jawaban")

    review = (
        db.query(KompasReview)
        .filter(KompasReview.username == username, KompasReview.week_start == week_start)
        .first()
    )
    if review is None:
        review = KompasReview(username=username, week_start=week_start)
        db.add(review)
    review.built, review.improve, review.proud = built, improve, proud
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review
