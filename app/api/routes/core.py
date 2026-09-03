import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.ingestion.core_processor import process_dataset
from app.models import CoreTransaction, Dataset

router = APIRouter(prefix="/datasets", tags=["core"], dependencies=[Depends(require_dashboard_session)])


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


@router.get("/{dataset_id}/quality")
def get_dataset_quality(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Step "Validasi" di pipeline testing Laboratorium. Skor & isu dihitung
    LANGSUNG dari core_transactions yang ada (bukan angka karangan) — kalau
    dataset belum pernah di-Process, semua field kosong/None supaya
    frontend tahu harus jalankan step Bersihkan Data dulu.
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    total_rows = (
        db.query(func.count(CoreTransaction.id))
        .filter(CoreTransaction.dataset_id == dataset_id)
        .scalar()
    )

    if not total_rows:
        return {
            "processed": False,
            "total_rows": 0,
            "quality_score": None,
            "missing_date": 0,
            "missing_subtotal": 0,
            "missing_product": 0,
            "duplicate_order_ids": 0,
            "warnings": [],
            "errors": ["Dataset belum diproses — jalankan step Bersihkan Data dulu."],
        }

    missing_date = (
        db.query(func.count(CoreTransaction.id))
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.transaction_date.is_(None))
        .scalar()
    )
    missing_subtotal = (
        db.query(func.count(CoreTransaction.id))
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.subtotal.is_(None))
        .scalar()
    )
    missing_product = (
        db.query(func.count(CoreTransaction.id))
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.product_name.is_(None))
        .scalar()
    )
    dup_rows = (
        db.query(CoreTransaction.order_id, func.count(CoreTransaction.id).label("n"))
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.order_id.isnot(None))
        .group_by(CoreTransaction.order_id)
        .having(func.count(CoreTransaction.id) > 1)
        .all()
    )
    # Jumlah baris LEBIH dari kemunculan pertama tiap order_id yang dobel
    # (misal order_id X muncul 3x -> 2 dihitung duplikat).
    duplicate_order_ids = sum(n - 1 for _, n in dup_rows)

    completeness = 1 - (missing_date + missing_subtotal + missing_product) / (3 * total_rows)
    duplicate_rate = duplicate_order_ids / total_rows
    quality_score = round(max(0.0, completeness - duplicate_rate) * 100, 1)

    warnings = []
    errors = []
    if missing_date > 0:
        warnings.append(f"{missing_date} baris tidak punya tanggal transaksi valid")
    if missing_subtotal > 0:
        warnings.append(f"{missing_subtotal} baris tidak punya subtotal valid")
    if missing_product > 0:
        warnings.append(f"{missing_product} baris tidak punya nama produk")
    if duplicate_order_ids > 0:
        warnings.append(f"{duplicate_order_ids} baris punya order_id duplikat")
    if quality_score < 70:
        errors.append("Skor kualitas data di bawah 70 — tinjau isu di atas sebelum promosi.")

    return {
        "processed": True,
        "total_rows": total_rows,
        "quality_score": quality_score,
        "missing_date": missing_date,
        "missing_subtotal": missing_subtotal,
        "missing_product": missing_product,
        "duplicate_order_ids": duplicate_order_ids,
        "warnings": warnings,
        "errors": errors,
    }


@router.get("/{dataset_id}/insights")
def get_dataset_insights(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Insight yang sudah dihitung dari core_transactions: revenue per bulan +
    growth, top produk, dan breakdown status. Kalau dataset belum pernah
    di-"Process", hasilnya kosong semua (bukan error) — caller (dashboard)
    yang menampilkan ajakan untuk klik Process dulu.
    """
    started = time.perf_counter()
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
            "metrics_computed": 0,
            "tables_computed": 0,
            "processing_seconds": round(time.perf_counter() - started, 3),
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
        # Metrik nyata yang dihitung: revenue+growth+order_count per bulan,
        # revenue+qty per top produk, count per status — bukan angka tetap.
        "metrics_computed": len(revenue_by_month) * 3 + len(top_products) * 2 + len(status_breakdown),
        "tables_computed": sum(
            1 for t in (revenue_by_month, top_products, status_breakdown) if len(t) > 0
        ),
        "processing_seconds": round(time.perf_counter() - started, 3),
    }
