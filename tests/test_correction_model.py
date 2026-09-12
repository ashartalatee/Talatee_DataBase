"""
Test untuk Correction Model (app/api/routes/data_trust.py + penerapannya di
app/ingestion/core_processor.py) — Data Trust Spec section 14.

DISABLE_LOGIN_FOR_LOCAL_DEV di app/security/dashboard_session.py sedang True
untuk pemakaian lokal, jadi endpoint /datasets/* bisa dipanggil langsung
lewat HTTP tanpa simulasi cookie login. Upload file tetap butuh API key
(mekanisme auth terpisah untuk /ingest/upload).

Jalankan (Postgres & MinIO harus jalan lewat `docker compose up -d`):
    pytest tests/test_correction_model.py -v
"""
import secrets

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.ingestion.core_processor import process_dataset
from app.main import app
from app.models import ApiKey, CoreTransaction
from app.security.api_key import hash_key

client = TestClient(app)


def _unique_suffix() -> str:
    return secrets.token_hex(4)


@pytest.fixture(scope="module")
def api_key_header():
    plaintext_key = f"tal_test_correction_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="Correction Test Key",
            key_hash=hash_key(plaintext_key),
            key_prefix=plaintext_key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {plaintext_key}"}


def _upload(api_key_header, csv_bytes: bytes, filename: str) -> str:
    suffix = _unique_suffix()
    data = {
        "business_name": f"Correction Business {suffix}",
        "business_category": "lainnya",
        "source_name": f"Correction Source {suffix}",
        "dataset_name": f"Correction Dataset {suffix}",
    }
    r = client.post(
        "/ingest/upload",
        data=data,
        files={"file": (filename, csv_bytes, "text/csv")},
        headers=api_key_header,
    )
    assert r.status_code == 201
    return r.json()["dataset_id"]


def test_correction_applies_after_reprocess_but_not_before(api_key_header):
    """
    Correction TIDAK langsung mengubah core_transactions saat diajukan --
    baru berlaku setelah 'Bersihkan Data' (process_dataset) dijalankan lagi.
    """
    csv_content = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-CORR-1,2026-01-01,Serum A,1,89000,89000,Completed\n"
    )
    dataset_id = _upload(api_key_header, csv_content, "correction_test.csv")

    db = SessionLocal()
    process_dataset(db, dataset_id)
    row_before = (
        db.query(CoreTransaction)
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.order_id == "ORD-CORR-1")
        .first()
    )
    assert row_before.subtotal == 89000
    db.close()

    # Ajukan correction: harga aslinya salah, seharusnya 99000.
    r = client.post(
        f"/datasets/{dataset_id}/corrections",
        json={
            "order_id": "ORD-CORR-1",
            "field_name": "subtotal",
            "corrected_value": "99000",
            "reason": "Harga salah input di sumber",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["correction_version"] == 1
    assert body["original_value"] == "89000.00"

    # Sebelum reprocess, core_transactions BELUM berubah.
    db = SessionLocal()
    row_still_old = (
        db.query(CoreTransaction)
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.order_id == "ORD-CORR-1")
        .first()
    )
    assert row_still_old.subtotal == 89000
    db.close()

    # Reprocess -- SEKARANG correction diterapkan.
    db = SessionLocal()
    summary = process_dataset(db, dataset_id)
    assert summary["corrections_applied"] == 1

    row_after = (
        db.query(CoreTransaction)
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.order_id == "ORD-CORR-1")
        .first()
    )
    assert row_after.subtotal == 99000
    db.close()


def test_correction_versioning_and_latest_wins(api_key_header):
    """Correction kedua untuk field yang sama harus dapat version 2, dan
    yang diterapkan adalah versi TERBARU, bukan yang pertama."""
    csv_content = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-CORR-2,2026-01-01,Serum B,1,50000,50000,Completed\n"
    )
    dataset_id = _upload(api_key_header, csv_content, "correction_version_test.csv")

    db = SessionLocal()
    process_dataset(db, dataset_id)
    db.close()

    r1 = client.post(
        f"/datasets/{dataset_id}/corrections",
        json={
            "order_id": "ORD-CORR-2",
            "field_name": "subtotal",
            "corrected_value": "60000",
            "reason": "Koreksi pertama",
        },
    )
    assert r1.json()["correction_version"] == 1

    r2 = client.post(
        f"/datasets/{dataset_id}/corrections",
        json={
            "order_id": "ORD-CORR-2",
            "field_name": "subtotal",
            "corrected_value": "70000",
            "reason": "Koreksi kedua, angka pertama masih salah",
        },
    )
    assert r2.json()["correction_version"] == 2

    db = SessionLocal()
    process_dataset(db, dataset_id)
    row = (
        db.query(CoreTransaction)
        .filter(CoreTransaction.dataset_id == dataset_id, CoreTransaction.order_id == "ORD-CORR-2")
        .first()
    )
    assert row.subtotal == 70000  # versi TERBARU (v2) yang menang, bukan v1
    db.close()

    # Riwayat lengkap (bukan cuma yang aktif) harus tetap ada 2 baris.
    history = client.get(f"/datasets/{dataset_id}/corrections").json()
    assert len(history) == 2


def test_correction_rejects_non_correctable_field():
    """Field yang bukan bagian dari CORRECTABLE_FIELDS (mis. order_id
    sendiri) harus ditolak dengan 400, bukan diam-diam diterima."""
    db = SessionLocal()
    from app.models import Dataset, Source, Business
    import uuid as uuid_mod

    biz = Business(name=f"Reject Test {secrets.token_hex(4)}", category="lainnya")
    db.add(biz)
    db.flush()
    src = Source(business_id=biz.id, name="Reject Source", type="csv")
    db.add(src)
    db.flush()
    ds = Dataset(source_id=src.id, name="Reject Dataset")
    db.add(ds)
    db.commit()
    dataset_id = ds.id
    db.close()

    r = client.post(
        f"/datasets/{dataset_id}/corrections",
        json={
            "order_id": "ORD-X",
            "field_name": "order_id",
            "corrected_value": "ORD-Y",
            "reason": "Mencoba ganti identitas baris",
        },
    )
    assert r.status_code == 400
