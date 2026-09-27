"""
Talatee MCP server — read-only business-insight tools for Hermes.

Grounded in the schema that already exists in this repo:

    Business -> Source -> Dataset -> Batch -> CoreTransaction

Same Data Trust rule the dashboard already enforces (see
app/api/routes/core.py's /insights endpoint, Data Trust Spec Rule 06):
analytics only ever reads datasets with trust_status == "TRUSTED". A dataset
that hasn't been validated + promoted yet is silently excluded from every sum
below — never treated as zero — and every tool reports how many datasets were
skipped so a low number never looks like "no revenue" by mistake.

Every tool only ever runs one of the parameterized queries written here.
Hermes supplies business_name/dates/limit — never SQL.

Run standalone:
    python -m app.mcp.server

Then point Hermes at this process (see Hermes docs > MCP Integration).

Requires: mcp==1.30.0 (pin this — mcp>=2.0 renamed FastMCP to MCPServer and
this file will fail to import with a newer version).
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Batch, Business, CoreTransaction, Dataset, Source

mcp = FastMCP("talatee-business-data")

_NOT_TRASHED = (
    Batch.deleted_at.is_(None),
    Dataset.deleted_at.is_(None),
    Source.deleted_at.is_(None),
    Business.deleted_at.is_(None),
)
_TRUSTED = (Dataset.trust_status == "TRUSTED",)


def _get_business(db: Session, business_name: str) -> Optional[Business]:
    return (
        db.query(Business)
        .filter(
            func.lower(Business.name) == business_name.lower(),
            Business.deleted_at.is_(None),
        )
        .first()
    )


def _parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def _trusted_transactions(db: Session, business_id):
    """CoreTransaction rows for one business, chained through Batch -> Dataset
    -> Source -> Business, restricted to not-trashed + TRUSTED datasets."""
    return (
        db.query(CoreTransaction)
        .join(Batch, CoreTransaction.batch_id == Batch.id)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .join(Source, Dataset.source_id == Source.id)
        .join(Business, Source.business_id == Business.id)
        .filter(Business.id == business_id, *_NOT_TRASHED, *_TRUSTED)
    )


def _count_untrusted_datasets(db: Session, business_id) -> int:
    return (
        db.query(func.count(Dataset.id))
        .join(Source, Dataset.source_id == Source.id)
        .filter(
            Source.business_id == business_id,
            Dataset.deleted_at.is_(None),
            Source.deleted_at.is_(None),
            Dataset.trust_status != "TRUSTED",
        )
        .scalar()
        or 0
    )


@mcp.tool()
def get_business_summary(business_name: str) -> dict:
    """Ringkasan satu business (klien): kategori, status, omzet 30 hari
    terakhir dan jumlah transaksinya (hanya dari dataset yang sudah TRUSTED),
    plus berapa dataset yang belum trusted dan karena itu belum ikut dihitung."""
    with SessionLocal() as db:
        business = _get_business(db, business_name)
        if business is None:
            return {"error": f"business '{business_name}' tidak ditemukan"}

        since = dt.date.today() - dt.timedelta(days=30)
        omzet, jumlah = (
            _trusted_transactions(db, business.id)
            .filter(
                CoreTransaction.is_revenue.is_(True),
                CoreTransaction.transaction_date >= since,
            )
            .with_entities(
                func.coalesce(func.sum(CoreTransaction.subtotal), 0),
                func.count(CoreTransaction.id),
            )
            .one()
        )

        return {
            "business": business.name,
            "category": business.category,
            "status": business.status,
            "omzet_30_hari": float(omzet),
            "jumlah_transaksi_30_hari": int(jumlah),
            "dataset_belum_trusted": _count_untrusted_datasets(db, business.id),
        }


@mcp.tool()
def query_transactions(
    business_name: str,
    start_date: str,
    end_date: str,
    product_name: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Daftar transaksi (dari dataset TRUSTED saja) satu business dalam
    rentang tanggal (YYYY-MM-DD), opsional filter nama produk (partial
    match), maksimal `limit` baris."""
    with SessionLocal() as db:
        business = _get_business(db, business_name)
        if business is None:
            return [{"error": f"business '{business_name}' tidak ditemukan"}]

        q = _trusted_transactions(db, business.id).filter(
            CoreTransaction.transaction_date >= _parse_date(start_date),
            CoreTransaction.transaction_date <= _parse_date(end_date),
        )
        if product_name:
            q = q.filter(CoreTransaction.product_name.ilike(f"%{product_name}%"))

        rows = (
            q.order_by(CoreTransaction.transaction_date.desc())
            .limit(min(limit, 500))
            .all()
        )
        return [
            {
                "tanggal": t.transaction_date.isoformat() if t.transaction_date else None,
                "produk": t.product_name,
                "qty": t.qty,
                "harga_satuan": float(t.unit_price) if t.unit_price is not None else None,
                "subtotal": float(t.subtotal) if t.subtotal is not None else None,
                "status": t.status_raw,
            }
            for t in rows
        ]


@mcp.tool()
def get_sales_summary(business_name: str, start_date: str, end_date: str) -> dict:
    """Total omzet, jumlah transaksi, rata-rata per transaksi dalam satu
    rentang tanggal, dan perubahan persen terhadap periode sebelumnya yang
    panjangnya sama — hanya dari dataset TRUSTED."""
    with SessionLocal() as db:
        business = _get_business(db, business_name)
        if business is None:
            return {"error": f"business '{business_name}' tidak ditemukan"}

        d1, d2 = _parse_date(start_date), _parse_date(end_date)
        period_len = (d2 - d1).days + 1
        prev_d2 = d1 - dt.timedelta(days=1)
        prev_d1 = prev_d2 - dt.timedelta(days=period_len - 1)

        def _totals(lo: dt.date, hi: dt.date) -> tuple[float, int]:
            omzet, jumlah = (
                _trusted_transactions(db, business.id)
                .filter(
                    CoreTransaction.is_revenue.is_(True),
                    CoreTransaction.transaction_date >= lo,
                    CoreTransaction.transaction_date <= hi,
                )
                .with_entities(
                    func.coalesce(func.sum(CoreTransaction.subtotal), 0),
                    func.count(CoreTransaction.id),
                )
                .one()
            )
            return float(omzet), int(jumlah)

        omzet, jumlah = _totals(d1, d2)
        omzet_prev, _ = _totals(prev_d1, prev_d2)

        pct_change = None
        if omzet_prev > 0:
            pct_change = round((omzet - omzet_prev) / omzet_prev * 100, 1)

        return {
            "business": business.name,
            "periode": f"{start_date} s/d {end_date}",
            "total_omzet": omzet,
            "total_transaksi": jumlah,
            "rata_rata_transaksi": round(omzet / jumlah, 2) if jumlah else 0,
            "perubahan_vs_periode_sebelumnya_persen": pct_change,
            "dataset_belum_trusted": _count_untrusted_datasets(db, business.id),
        }


@mcp.tool()
def get_top_products(
    business_name: str, start_date: str, end_date: str, limit: int = 5
) -> list[dict]:
    """Produk terlaris satu business dalam rentang tanggal (dataset TRUSTED
    saja), diurutkan berdasarkan omzet."""
    with SessionLocal() as db:
        business = _get_business(db, business_name)
        if business is None:
            return [{"error": f"business '{business_name}' tidak ditemukan"}]

        rows = (
            _trusted_transactions(db, business.id)
            .filter(
                CoreTransaction.is_revenue.is_(True),
                CoreTransaction.product_name.isnot(None),
                CoreTransaction.transaction_date >= _parse_date(start_date),
                CoreTransaction.transaction_date <= _parse_date(end_date),
            )
            .with_entities(
                CoreTransaction.product_name,
                func.coalesce(func.sum(CoreTransaction.subtotal), 0),
                func.coalesce(func.sum(CoreTransaction.qty), 0),
            )
            .group_by(CoreTransaction.product_name)
            .order_by(func.sum(CoreTransaction.subtotal).desc())
            .limit(min(limit, 50))
            .all()
        )
        return [
            {"produk": name, "omzet": float(omzet), "qty_terjual": int(qty)}
            for name, omzet, qty in rows
        ]


@mcp.tool()
def list_businesses() -> list[dict]:
    """Daftar semua business (klien) yang terdaftar di Talatee -- nama
    persis, kategori, status, dan berapa dataset yang belum trusted. Panggil
    ini dulu kalau belum tahu nama persis business yang mau ditanya, karena
    tools lain (get_business_summary, dkk) butuh nama yang cocok persis."""
    with SessionLocal() as db:
        rows = (
            db.query(Business)
            .filter(Business.deleted_at.is_(None))
            .order_by(Business.name)
            .all()
        )
        return [
            {
                "business": b.name,
                "category": b.category,
                "status": b.status,
                "dataset_belum_trusted": _count_untrusted_datasets(db, b.id),
            }
            for b in rows
        ]


if __name__ == "__main__":
    mcp.run()
