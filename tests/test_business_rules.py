"""
Test untuk business rule validation di app/api/routes/core.py::_compute_quality
(qty x unit_price = subtotal) — ditambahkan 4 September 2026, lihat Data
Trust Spec section 9.7 & 10 (business rule mismatch = CRITICAL ERROR).

Sama seperti tests/test_core_processor_dedup.py: upload lewat /ingest/upload
asli (API key), lalu proses & cek kualitas langsung lewat pemanggilan fungsi
(bukan HTTP /datasets/{id}/quality) supaya tidak perlu dashboard session auth.

Jalankan (Postgres & MinIO harus jalan lewat `docker compose up -d`):
    pytest tests/test_business_rules.py -v
"""
import secrets
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.routes.core import _compute_quality
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
    plaintext_key = f"tal_test_bizrules_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="Business Rules Test Key",
            key_hash=hash_key(plaintext_key),
            key_prefix=plaintext_key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {plaintext_key}"}


def _upload_and_process(api_key_header, csv_bytes: bytes, filename: str):
    suffix = _unique_suffix()
    data = {
        "business_name": f"BizRules Business {suffix}",
        "business_category": "lainnya",
        "source_name": f"BizRules Source {suffix}",
        "dataset_name": f"BizRules Dataset {suffix}",
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
    try:
        process_dataset(db, dataset_id)
        return dataset_id, db
    except Exception:
        db.close()
        raise


def test_subtotal_matching_qty_times_price_has_no_error(api_key_header):
    """qty x unit_price == subtotal untuk semua baris -> tidak ada error
    business rule sama sekali, quality_score tetap 100."""
    csv_ok = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-OK-1,2026-01-01,Serum A,2,50000,100000,Completed\n"
        b"ORD-OK-2,2026-01-02,Serum B,3,25000,75000,Completed\n"
    )
    dataset_id, db = _upload_and_process(api_key_header, csv_ok, "bizrules_ok.csv")
    try:
        result = _compute_quality(db, dataset_id)
        assert result["subtotal_mismatch"] == 0
        assert result["subtotal_mismatch_examples"] == []
        assert result["errors"] == []
        assert result["quality_score"] == 100.0
    finally:
        db.close()


def test_subtotal_mismatch_is_flagged_as_critical_error(api_key_header):
    """qty x unit_price != subtotal di 1 baris dari 2 -> harus kedetek
    sebagai error (BLOCK), bukan cuma warning, dan turunkan quality_score."""
    csv_mismatch = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-BAD-1,2026-01-01,Serum A,2,50000,999999,Completed\n"  # 2x50000=100000, bukan 999999
        b"ORD-BAD-2,2026-01-02,Serum B,3,25000,75000,Completed\n"  # ini benar
    )
    dataset_id, db = _upload_and_process(api_key_header, csv_mismatch, "bizrules_bad.csv")
    try:
        result = _compute_quality(db, dataset_id)
        assert result["subtotal_mismatch"] == 1
        assert len(result["subtotal_mismatch_examples"]) == 1
        # Bandingkan sebagai angka (bukan exact string) — unit_price tersimpan
        # Numeric(14,2), jadi hasil kali Decimal-nya "100000.00" bukan "100000",
        # nilainya tetap benar cuma beda presisi tampilan.
        expected = Decimal(result["subtotal_mismatch_examples"][0]["expected_subtotal"])
        assert expected == Decimal("100000")

        # Harus masuk 'errors' (CRITICAL/BLOCK), bukan cuma 'warnings'.
        assert any("subtotal" in e and "tidak cocok" in e for e in result["errors"])

        # 1 dari 2 baris salah -> skor kualitas pasti < 100.
        assert result["quality_score"] < 100.0
    finally:
        db.close()
