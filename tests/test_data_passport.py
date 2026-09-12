"""
Test untuk Data Passport (app/api/routes/data_trust.py::get_data_passport) —
Data Trust Spec section 6: 1 endpoint yang merangkum provenance, status
kualitas, dan riwayat koreksi/reconciliation dataset.

Jalankan (Postgres & MinIO harus jalan lewat `docker compose up -d`):
    pytest tests/test_data_passport.py -v
"""
import secrets

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
    plaintext_key = f"tal_test_passport_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="Passport Test Key",
            key_hash=hash_key(plaintext_key),
            key_prefix=plaintext_key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {plaintext_key}"}


def test_passport_summarizes_provenance_and_quality(api_key_header):
    suffix = _unique_suffix()
    data = {
        "business_name": f"Passport Business {suffix}",
        "business_category": "lainnya",
        "source_name": f"Passport Source {suffix}",
        "dataset_name": f"Passport Dataset {suffix}",
    }
    csv_content = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-PASS-1,2026-01-01,Serum A,1,50000,50000,Completed\n"
        b"ORD-PASS-2,2026-01-02,Serum B,1,30000,30000,Completed\n"
    )
    r = client.post(
        "/ingest/upload",
        data=data,
        files={"file": ("passport_test.csv", csv_content, "text/csv")},
        headers=api_key_header,
    )
    assert r.status_code == 201
    dataset_id = r.json()["dataset_id"]

    db = SessionLocal()
    process_dataset(db, dataset_id)
    db.close()

    passport = client.get(f"/datasets/{dataset_id}/passport").json()

    # Identitas & trust status dataset.
    assert passport["dataset"]["id"] == dataset_id
    assert passport["dataset"]["trust_status"] == "INGESTED"  # belum divalidasi/promote

    # Provenance: 1 batch, dari 1 file, dengan checksum tercatat.
    assert passport["provenance"]["total_batches"] == 1
    assert passport["provenance"]["total_raw_records"] == 2
    assert passport["provenance"]["sources"][0]["filename"] == "passport_test.csv"
    assert passport["provenance"]["sources"][0]["checksum"]  # tidak kosong

    # Current state: quality score dihitung, 2 record di core.
    assert passport["current_state"]["total_records_in_core"] == 2
    assert passport["current_state"]["quality_score"] == 100.0

    # Belum ada correction/reconciliation.
    assert passport["corrections"]["total_applied_ever"] == 0
    assert passport["reconciliation"] is None


def test_passport_reflects_correction_count(api_key_header):
    suffix = _unique_suffix()
    data = {
        "business_name": f"Passport Corr Business {suffix}",
        "business_category": "lainnya",
        "source_name": f"Passport Corr Source {suffix}",
        "dataset_name": f"Passport Corr Dataset {suffix}",
    }
    csv_content = (
        b"order_id,tanggal,produk,qty,harga_satuan,subtotal,status\n"
        b"ORD-PASS-3,2026-01-01,Serum A,1,50000,50000,Completed\n"
    )
    r = client.post(
        "/ingest/upload",
        data=data,
        files={"file": ("passport_corr.csv", csv_content, "text/csv")},
        headers=api_key_header,
    )
    dataset_id = r.json()["dataset_id"]

    db = SessionLocal()
    process_dataset(db, dataset_id)
    db.close()

    client.post(
        f"/datasets/{dataset_id}/corrections",
        json={
            "order_id": "ORD-PASS-3",
            "field_name": "subtotal",
            "corrected_value": "55000",
            "reason": "Test passport correction count",
        },
    )

    passport = client.get(f"/datasets/{dataset_id}/passport").json()
    assert passport["corrections"]["total_applied_ever"] == 1


def test_passport_404_for_unknown_dataset():
    import uuid

    r = client.get(f"/datasets/{uuid.uuid4()}/passport")
    assert r.status_code == 404
