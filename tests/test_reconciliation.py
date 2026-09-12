"""
Test untuk Reconciliation (app/api/routes/data_trust.py) — Data Trust Spec
section 16: banding SOURCE TOTAL (dari luar Talatee) vs TALATEE TOTAL
(dihitung dari core_transactions yang is_revenue=True).

Jalankan (Postgres & MinIO harus jalan lewat `docker compose up -d`):
    pytest tests/test_reconciliation.py -v
"""
import secrets
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.ingestion.core_processor import process_dataset
from app.main import app
from app.models import ApiKey
from app.security.api_key import hash_key

client = TestClient(app)


def _unique_suffix() -> str:
    return secrets.token_hex(4)


@pytest.fixture(scope="module")
def api_key_header():
    plaintext_key = f"tal_test_reconciliation_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="Reconciliation Test Key",
            key_hash=hash_key(plaintext_key),
            key_prefix=plaintext_key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {plaintext_key}"}


def _upload_and_process(api_key_header, csv_bytes: bytes, filename: str) -> str:
    suffix = _unique_suffix()
    data = {
        "business_name": f"Reconciliation Business {suffix}",
        "business_category": "lainnya",
        "source_name": f"Reconciliation Source {suffix}",
        "dataset_name": f"Reconciliation Dataset {suffix}",
    }
    r = client.post(
        "/ingest/upload",
        data=data,
        files={"file": (filename, csv_bytes, "text/csv")},
        headers=api_key_header,
    )
    assert r.status_code == 201
    dataset_id = r.json()["dataset_id"]

    db = SessionLocal()
    process_dataset(db, dataset_id)
    db.close()
    return dataset_id


def test_reconciliation_passes_when_totals_match(api_key_header):
    """2 transaksi Completed bulan Januari 2026: 100000 + 75000 = 175000.
    Kalau source_total juga 175000, statusnya harus PASSED."""
    csv_content = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-REC-1,2026-01-05,Serum A,2,50000,100000,Completed\n"
        b"ORD-REC-2,2026-01-10,Serum B,3,25000,75000,Completed\n"
    )
    dataset_id = _upload_and_process(api_key_header, csv_content, "reconciliation_match.csv")

    r = client.post(
        f"/datasets/{dataset_id}/reconciliation",
        json={"period_label": "2026-01", "source_total": "175000"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "PASSED"
    assert Decimal(body["talatee_total"]) == Decimal("175000")
    assert Decimal(body["difference"]) == Decimal("0")
    assert body["hint"] is None


def test_reconciliation_fails_when_totals_differ_beyond_tolerance(api_key_header):
    """source_total beda jauh dari talatee_total -> FAILED, dengan hint
    yang menjelaskan kemungkinan penyebab."""
    csv_content = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-REC-3,2026-02-01,Serum C,1,60000,60000,Completed\n"
    )
    dataset_id = _upload_and_process(api_key_header, csv_content, "reconciliation_mismatch.csv")

    r = client.post(
        f"/datasets/{dataset_id}/reconciliation",
        json={
            "period_label": "2026-02",
            "source_total": "500000",
            "notes": "Ada transaksi WA yang belum masuk sistem",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "FAILED"
    assert Decimal(body["difference"]) == Decimal("440000")
    assert body["hint"] is not None


def test_non_revenue_transactions_excluded_from_talatee_total(api_key_header):
    """Transaksi berstatus Cancelled TIDAK boleh ikut dihitung di
    talatee_total (is_revenue=False) -- kalau ikut, reconciliation akan
    salah dan menyesatkan."""
    csv_content = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-REC-4,2026-03-01,Serum D,1,80000,80000,Completed\n"
        b"ORD-REC-5,2026-03-02,Serum E,1,999999,999999,Cancelled\n"
    )
    dataset_id = _upload_and_process(api_key_header, csv_content, "reconciliation_cancelled.csv")

    r = client.post(
        f"/datasets/{dataset_id}/reconciliation",
        json={"period_label": "2026-03", "source_total": "80000"},
    )
    body = r.json()
    assert Decimal(body["talatee_total"]) == Decimal("80000")  # bukan 1079999
    assert body["status"] == "PASSED"


def test_reconciliation_history_is_listed_newest_first(api_key_header):
    csv_content = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-REC-6,2026-04-01,Serum F,1,10000,10000,Completed\n"
    )
    dataset_id = _upload_and_process(api_key_header, csv_content, "reconciliation_history.csv")

    client.post(f"/datasets/{dataset_id}/reconciliation", json={"period_label": "2026-04", "source_total": "10000"})
    client.post(f"/datasets/{dataset_id}/reconciliation", json={"period_label": "2026-04", "source_total": "999"})

    history = client.get(f"/datasets/{dataset_id}/reconciliation").json()
    assert len(history) == 2
    assert history[0]["status"] == "FAILED"  # yang terbaru (source_total=999)
    assert history[1]["status"] == "PASSED"
