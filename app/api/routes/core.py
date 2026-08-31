import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ingestion.core_processor import process_dataset
from app.models import CoreTransaction, Dataset

router = APIRouter(prefix="/datasets", tags=["core"])


@router.post("/{dataset_id}/process")
def process_dataset_endpoint(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Trigger layer Raw -> Core untuk SEMUA batch (sukses) di dataset ini.
    Dipicu manual (tombol "Process Data" di dashboard) — bukan otomatis
    tiap ada batch baru, supaya kamu bisa cek hasilnya dulu sebelum
    dipercaya penuh. Aman dipanggil berkali-kali (idempotent per batch).
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    summary = process_dataset(db, dataset_id)
    return summary


@router.get("/{dataset_id}/insights")
def get_dataset_insights(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Insight yang sudah dihitung dari core_transactions: revenue per bulan +
    growth, top produk, dan breakdown status. Kalau dataset belum pernah
    di-"Process", hasilnya kosong semua (bukan error) — caller (dashboard)
    yang menampilkan ajakan untuk klik Process dulu.
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    base = db.query(CoreTransaction).filter(CoreTransaction.dataset_id == dataset_id)
    total_rows = base.count()

    if total_rows == 0:
        return {
            "processed": False,
            "total_rows": 0,
            "revenue_by_month": [],
            "top_products": [],
            "status_breakdown": [],
        }

    # Revenue & jumlah order per bulan (hanya baris is_revenue=True)
    month_expr = func.to_char(CoreTransaction.transaction_date, "YYYY-MM")
    revenue_rows = (
        db.query(
            month_expr.label("month"),
            func.coalesce(func.sum(CoreTransaction.subtotal), 0).label("revenue"),
            func.count(CoreTransaction.id).label("order_count"),
        )
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.is_revenue.is_(True))
        .group_by(month_expr)
        .order_by(month_expr)
        .all()
    )
    revenue_by_month = [
        {"month": r.month, "revenue": float(r.revenue), "order_count": r.order_count}
        for r in revenue_rows
        if r.month is not None
    ]
    # Growth % month-over-month, dihitung di Python supaya query tetap simpel.
    for i, row in enumerate(revenue_by_month):
        if i == 0 or revenue_by_month[i - 1]["revenue"] == 0:
            row["growth_pct"] = None
        else:
            prev = revenue_by_month[i - 1]["revenue"]
            row["growth_pct"] = round((row["revenue"] - prev) / prev * 100, 1)

    # Top produk berdasarkan total revenue (hanya transaksi is_revenue=True)
    top_products_rows = (
        db.query(
            CoreTransaction.product_name,
            func.coalesce(func.sum(CoreTransaction.subtotal), 0).label("revenue"),
            func.coalesce(func.sum(CoreTransaction.qty), 0).label("qty_sold"),
        )
        .filter(
            CoreTransaction.dataset_id == dataset_id,
            CoreTransaction.is_revenue.is_(True),
            CoreTransaction.product_name.isnot(None),
        )
        .group_by(CoreTransaction.product_name)
        .order_by(func.sum(CoreTransaction.subtotal).desc())
        .limit(10)
        .all()
    )
    top_products = [
        {"product_name": r.product_name, "revenue": float(r.revenue), "qty_sold": r.qty_sold}
        for r in top_products_rows
    ]

    # Breakdown status (semua baris, bukan cuma yang is_revenue)
    status_rows = (
        db.query(
            CoreTransaction.status_raw,
            func.count(CoreTransaction.id).label("count"),
        )
        .filter(CoreTransaction.dataset_id == dataset_id)
        .group_by(CoreTransaction.status_raw)
        .order_by(func.count(CoreTransaction.id).desc())
        .all()
    )
    status_breakdown = [{"status": r.status_raw or "(kosong)", "count": r.count} for r in status_rows]

    return {
        "processed": True,
        "total_rows": total_rows,
        "revenue_by_month": revenue_by_month,
        "top_products": top_products,
        "status_breakdown": status_breakdown,
    }
