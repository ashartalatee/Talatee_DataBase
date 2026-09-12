import time
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dashboard_session import require_dashboard_session
from app.ingestion.core_processor import process_dataset
from app.models import CoreTransaction, Dataset
from app.services import trash as trash_service

router = APIRouter(prefix="/datasets", tags=["core"], dependencies=[Depends(require_dashboard_session)])


@router.post("/{dataset_id}/process")
def process_dataset_endpoint(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Trigger layer Raw -> Core untuk SEMUA batch (sukses) di dataset ini.
    Dipicu manual (tombol "Process Data" di dashboard) — bukan otomatis
    tiap ada batch baru, supaya kamu bisa cek hasilnya dulu sebelum
    dipercaya penuh. Aman dipanggil berkali-kali (idempotent per batch).

    Trust reset: reprocessing mengganti isi core_transactions, jadi status
    trust lama (termasuk TRUSTED) sudah tidak lagi berdasarkan data yang
    sama persis. Data Trust Spec section 12/7 — trust harus diperoleh ulang,
    bukan dibawa otomatis dari promosi sebelumnya.
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    summary = process_dataset(db, dataset_id)

    if dataset.trust_status != "INGESTED":
        dataset.trust_status = "INGESTED"
        db.commit()

    return summary


def _compute_quality(db: Session, dataset_id: uuid.UUID) -> dict:
    """Hitung quality score & isu LANGSUNG dari core_transactions yang ada
    (bukan angka karangan). Dipakai bersama oleh GET /quality (baca saja)
    dan POST /promote (baca + jadi syarat promosi trust_status)."""
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

    # Business rule (Data Trust Spec section 9.7): qty x unit_price harus
    # sama dengan subtotal. Dicek di Python (bukan SQL) karena datasetnya
    # skala personal/kecil dan expected value butuh perkalian Decimal yang
    # presisi — lebih gampang dibaca & di-debug lewat mismatch_examples.
    qty_price_rows = (
        db.query(
            CoreTransaction.id,
            CoreTransaction.order_id,
            CoreTransaction.qty,
            CoreTransaction.unit_price,
            CoreTransaction.subtotal,
        )
        .filter(
            CoreTransaction.dataset_id == dataset_id,
            CoreTransaction.qty.isnot(None),
            CoreTransaction.unit_price.isnot(None),
            CoreTransaction.subtotal.isnot(None),
        )
        .all()
    )
    subtotal_mismatch = 0
    mismatch_examples = []
    for row_id, order_id, qty, unit_price, subtotal in qty_price_rows:
        expected = Decimal(qty) * Decimal(unit_price)
        if expected != Decimal(subtotal):
            subtotal_mismatch += 1
            if len(mismatch_examples) < 5:  # cukup contoh, bukan dump semua baris
                mismatch_examples.append(
                    {
                        "row_id": str(row_id),
                        "order_id": order_id,
                        "qty": qty,
                        "unit_price": str(unit_price),
                        "subtotal": str(subtotal),
                        "expected_subtotal": str(expected),
                    }
                )

    completeness = 1 - (missing_date + missing_subtotal + missing_product) / (3 * total_rows)
    duplicate_rate = duplicate_order_ids / total_rows
    business_rule_rate = subtotal_mismatch / total_rows
    quality_score = round(max(0.0, completeness - duplicate_rate - business_rule_rate) * 100, 1)

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
    if subtotal_mismatch > 0:
        # CRITICAL sesuai spec section 9.7/10 — subtotal yang salah hitung
        # langsung merusak angka revenue di Analytics, jadi masuk errors
        # (BLOCK), bukan warnings (NEEDS_REVIEW biasa).
        errors.append(
            f"{subtotal_mismatch} baris punya subtotal yang tidak cocok dengan qty x harga_satuan"
        )
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
        "subtotal_mismatch": subtotal_mismatch,
        "subtotal_mismatch_examples": mismatch_examples,
        "warnings": warnings,
        "errors": errors,
    }


@router.get("/{dataset_id}/quality")
def get_dataset_quality(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Step "Validasi" di pipeline testing Laboratorium. Efek samping: kolom
    trust_status dataset ini diperbarui supaya mencerminkan hasil quality
    check TERBARU (Data Trust Spec section 7 — lifecycle). Tidak pernah naik
    ke TRUSTED di sini (itu wajib lewat POST /promote yang eksplisit), tapi
    BISA diturunkan dari TRUSTED kalau ternyata ada error baru terdeteksi —
    trust yang sudah diberi tidak boleh dianggap permanen kalau datanya
    ternyata bermasalah (Rule 04: never silently fail).
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    result = _compute_quality(db, dataset_id)

    if not result["processed"]:
        new_status = "INGESTED"
    elif result["errors"]:
        new_status = "NEEDS_REVIEW"
    elif dataset.trust_status == "TRUSTED":
        new_status = "TRUSTED"  # sudah pernah di-promote & tidak ada error baru — pertahankan
    else:
        new_status = "VALIDATING"  # lolos quality check, tapi belum di-promote eksplisit

    if dataset.trust_status != new_status:
        dataset.trust_status = new_status
        db.commit()

    result["trust_status"] = new_status
    return result


@router.post("/{dataset_id}/promote")
def promote_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Naikkan trust_status dataset menjadi TRUSTED — SATU-SATUNYA jalan untuk
    mencapai status ini (Data Trust Spec section 12: "Jangan otomatis:
    Quality > 90 = TRUSTED"). Ditolak (400) kalau quality check belum pernah
    jalan atau masih ada error yang belum ditinjau.

    Catatan jujur untuk UI: TRUSTED versi ini berarti "lolos completeness,
    duplicate check, DAN business rule qty x harga_satuan = subtotal"
    (ditambahkan 4 September 2026) — tapi belum berarti "semua data akurat
    100% secara dunia nyata" (lihat Data Trust Spec section 36: Trusted =
    memenuhi aturan verifikasi yang ditentukan, bukan jaminan mutlak).
    Business rule lain yang mungkin relevan tapi belum dicek: konsistensi
    harga per produk antar transaksi, kategori/status yang valid dari
    daftar enum tertentu, dsb — belum ada karena belum ada kebutuhan nyata
    yang mengharuskannya (lihat prinsip "Do Not Overengineer" section 40).
    """
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    result = _compute_quality(db, dataset_id)

    if not result["processed"]:
        raise HTTPException(
            status_code=400,
            detail="Dataset belum diproses — jalankan Bersihkan Data lalu Validasi dulu sebelum promote.",
        )
    if result["errors"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Dataset masih punya error yang belum ditinjau — tidak bisa di-promote ke TRUSTED.",
                "errors": result["errors"],
                "warnings": result["warnings"],
            },
        )

    dataset.trust_status = "TRUSTED"
    db.commit()

    return {
        "trust_status": "TRUSTED",
        "quality_score": result["quality_score"],
        "total_rows": result["total_rows"],
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
    if dataset is None or not trash_service.is_dataset_visible(db, dataset):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    # Gate: Analytics production hanya boleh pakai TRUSTED data (Data Trust
    # Spec Rule 06 / section 34). Bukan error 4xx karena ini bukan input
    # salah dari user — cuma dependency pipeline yang belum terpenuhi, jadi
    # dikembalikan sebagai status "blocked" biar frontend bisa tampilkan
    # ajakan yang jelas (mis. "jalankan Validasi lalu Promote dulu").
    if dataset.trust_status != "TRUSTED":
        return {
            "blocked": True,
            "trust_status": dataset.trust_status,
            "reason": (
                "Dataset belum berstatus TRUSTED — jalankan Validasi (dan "
                "perbaiki error jika ada), lalu promote dataset dulu sebelum "
                "Analisis/Insight boleh dihitung."
            ),
            "processed": False,
            "total_rows": 0,
            "revenue_by_month": [],
            "top_products": [],
            "status_breakdown": [],
            "metrics_computed": 0,
            "tables_computed": 0,
            "processing_seconds": round(time.perf_counter() - started, 3),
        }

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
