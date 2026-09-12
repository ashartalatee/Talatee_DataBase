"""
Test untuk process_dataset() di app/ingestion/core_processor.py — khususnya
kebijakan dedup lintas-batch yang ditambahkan 4 September 2026 (lihat
PROJECT_CONTEXT_TALATEE.md bagian 6b/7 & docstring core_processor.py).

Dites langsung lewat pemanggilan fungsi process_dataset() (bukan lewat HTTP
/datasets/{id}/process) supaya tidak perlu mengurus dashboard session auth —
upload batch-nya sendiri tetap lewat endpoint /ingest/upload asli (butuh API
key, sama seperti test_ingestion_e2e.py) supaya raw file & batch row-nya
representatif seperti kondisi nyata, bukan dibuat manual di test.

Jalankan (Postgres & MinIO harus jalan lewat `docker compose up -d`):
    pytest tests/test_core_processor_dedup.py -v
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.ingestion.core_processor import process_dataset
from app.main import app
from app.models import ApiKey, CoreTransaction
from app.security.api_key import hash_key
import secrets

client = TestClient(app)


def _unique_suffix() -> str:
    """Supaya test bisa dijalankan berkali-kali (sendiri ATAU bareng test
    lain) tanpa numpuk ke dataset lama — /ingest/upload tampaknya reuse
    dataset yang sudah ada kalau nama business/source/dataset-nya sama
    persis, jadi tiap test run butuh nama yang benar-benar baru."""
    return secrets.token_hex(4)


@pytest.fixture(scope="module")
def api_key_header():
    plaintext_key = f"tal_test_dedup_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="Dedup Test Key",
            key_hash=hash_key(plaintext_key),
            key_prefix=plaintext_key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {plaintext_key}"}


def test_dedup_keeps_latest_upload_across_batches(api_key_header):
    """
    order_id yang sama muncul di 2 batch berbeda (upload ulang dengan
    subtotal yang beda, mensimulasikan revisi). process_dataset() harus:
      - cuma tulis 1 baris ke core_transactions untuk order_id itu,
      - yang tersimpan adalah versi dari batch yang diupload PALING BARU,
      - baris yang kalah tercatat di summary['duplicates_skipped'],
      - duplicate_count == jumlah baris yang di-skip.
    """
    suffix = _unique_suffix()
    data = {
        "business_name": f"Dedup Test Business {suffix}",
        "business_category": "lainnya",
        "source_name": f"Dedup Test Source {suffix}",
        "dataset_name": f"Dedup Test Dataset {suffix}",
    }

    csv_v1 = (
        b"order_id,tanggal,qty,harga_satuan,subtotal,status\n"
        b"ORD-1,2026-01-01,1,1000,1000,Completed\n"
    )
    csv_v2 = (
        b"order_id,tanggal,qty,harga_satuan,subtotal,status\n"
        b"ORD-1,2026-01-01,1,2000,2000,Completed\n"
    )

    r1 = client.post(
        "/ingest/upload",
        data=data,
        files={"file": ("dedup_v1.csv", csv_v1, "text/csv")},
        headers=api_key_header,
    )
    assert r1.status_code == 201
    dataset_id = r1.json()["dataset_id"]

    # Batch kedua diupload "belakangan" — started_at batch 2 otomatis lebih
    # baru dari batch 1 karena memang dibuat setelahnya di request terpisah.
    r2 = client.post(
        "/ingest/upload",
        data=data,
        files={"file": ("dedup_v2.csv", csv_v2, "text/csv")},
        headers=api_key_header,
    )
    assert r2.status_code == 201

    db = SessionLocal()
    try:
        summary = process_dataset(db, dataset_id)

        assert summary["duplicate_count"] == 1
        assert len(summary["duplicates_skipped"]) == 1
        assert summary["duplicates_skipped"][0]["order_id"] == "ORD-1"
        assert summary["duplicates_skipped"][0]["skipped_filename"] == "dedup_v1.csv"

        rows = (
            db.query(CoreTransaction)
            .filter(CoreTransaction.dataset_id == dataset_id)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].subtotal == Decimal("2000")  # versi TERBARU (v2) yang menang
    finally:
        db.close()


def test_dedup_within_same_batch(api_key_header):
    """order_id yang sama muncul 2x DALAM 1 file yang sama harus tetap
    dideteksi & di-dedup (bukan cuma dedup ANTAR batch)."""
    suffix = _unique_suffix()
    data = {
        "business_name": f"Dedup SameBatch Business {suffix}",
        "business_category": "lainnya",
        "source_name": f"Dedup SameBatch Source {suffix}",
        "dataset_name": f"Dedup SameBatch Dataset {suffix}",
    }

    csv_content = (
        b"order_id,tanggal,qty,harga_satuan,subtotal,status\n"
        b"ORD-A,2026-02-01,1,5000,5000,Completed\n"
        b"ORD-A,2026-02-01,1,7000,7000,Completed\n"  # order_id sama, muncul lagi di baris berikutnya
        b"ORD-B,2026-02-02,1,3000,3000,Completed\n"
    )

    r1 = client.post(
        "/ingest/upload",
        data=data,
        files={"file": ("same_batch.csv", csv_content, "text/csv")},
        headers=api_key_header,
    )
    assert r1.status_code == 201
    dataset_id = r1.json()["dataset_id"]

    db = SessionLocal()
    try:
        summary = process_dataset(db, dataset_id)

        assert summary["duplicate_count"] == 1  # 1 baris ORD-A yang kalah
        rows = (
            db.query(CoreTransaction)
            .filter(CoreTransaction.dataset_id == dataset_id)
            .all()
        )
        assert len(rows) == 2  # ORD-A (1x, versi terakhir) + ORD-B

        ord_a = [r for r in rows if r.order_id == "ORD-A"][0]
        assert ord_a.subtotal == Decimal("7000")  # okurensi TERAKHIR yang menang
    finally:
        db.close()
