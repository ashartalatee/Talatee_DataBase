"""Aturan omzet saat kolom status tidak ada (app/ingestion/core_processor.py).

- Kolom `status` TIDAK ada sama sekali: semua baris dihitung sebagai penjualan
  selesai, dan jumlahnya dilaporkan di ringkasan (status_assumed_rows).
- Kolom `status` ADA: aturan lama tetap berlaku (hanya status di
  REVENUE_STATUSES yang dihitung, `cancelled` tidak).
- Omzet di Overview baru terisi setelah dataset berstatus TRUSTED.
"""
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import ApiKey, CoreTransaction, Dataset
from app.security.api_key import hash_key

client = TestClient(app)

# Format ekspor toko: tanpa kolom status. Total subtotal = 34000.
TANPA_STATUS = (
    "tanggal,waktu,transaction_ref,produk,kategori,qty,harga_satuan,subtotal\n"
    "2026-09-11,10:00,R1,Celurit,Peralatan,1,5000,5000\n"
    "2026-09-11,10:00,R1,Pisau,Peralatan,2,7500,15000\n"
    "2026-09-11,11:00,R2,Celurit,Peralatan,1,5000,5000\n"
    "2026-09-11,12:00,R3,Parang,Peralatan,1,9000,9000\n"
).encode()

# File dengan kolom status: satu selesai, satu dibatalkan.
DENGAN_STATUS = (
    "order_id,tanggal,qty,harga_satuan,subtotal,status\n"
    "O1,2026-09-11,2,5000,10000,completed\n"
    "O2,2026-09-11,1,7500,7500,cancelled\n"
).encode()


@pytest.fixture(scope="module")
def api_key_header():
    key = f"tal_test_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="Status Assumed Test Key",
            key_hash=hash_key(key),
            key_prefix=key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {key}"}


def _upload_and_process(headers, content):
    tag = uuid.uuid4().hex[:8]
    r = client.post(
        "/ingest/upload",
        headers=headers,
        data={
            "business_name": f"SA Biz {tag}",
            "business_category": "lainnya",
            "source_name": f"SA Src {tag}",
            "dataset_name": f"SA DS {tag}",
        },
        files={"file": ("ekspor.csv", content, "text/csv")},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "success", r.json().get("error_message")
    db = SessionLocal()
    try:
        ds_id = db.query(Dataset).filter(Dataset.name == f"SA DS {tag}").first().id
    finally:
        db.close()
    p = client.post(f"/datasets/{ds_id}/process")
    assert p.status_code == 200, p.text
    return ds_id, p.json()


def _rows(ds_id):
    db = SessionLocal()
    try:
        return (
            db.query(CoreTransaction)
            .filter(CoreTransaction.dataset_id == ds_id)
            .all()
        )
    finally:
        db.close()


def _revenue():
    r = client.get("/stats/overview")
    assert r.status_code == 200
    return r.json()["total_revenue"]


def test_no_status_column_counts_all_rows_and_reports_it(api_key_header):
    ds_id, summary = _upload_and_process(api_key_header, TANPA_STATUS)
    rows = _rows(ds_id)
    assert len(rows) == 4
    assert all(r.is_revenue for r in rows)
    assert summary["status_assumed_rows"] == 4


def test_status_column_keeps_the_original_rule(api_key_header):
    ds_id, summary = _upload_and_process(api_key_header, DENGAN_STATUS)
    by_order = {r.order_id: r for r in _rows(ds_id)}
    assert by_order["O1"].is_revenue is True
    assert by_order["O2"].is_revenue is False  # cancelled tidak dihitung
    assert summary["status_assumed_rows"] == 0


def test_overview_revenue_appears_only_after_dataset_is_trusted(api_key_header):
    before = _revenue()
    ds_id, _ = _upload_and_process(api_key_header, TANPA_STATUS)

    assert _revenue() == pytest.approx(before)  # belum TRUSTED: omzet tidak naik

    db = SessionLocal()
    try:
        db.get(Dataset, ds_id).trust_status = "TRUSTED"
        db.commit()
    finally:
        db.close()

    assert _revenue() - before == pytest.approx(34000)
