"""Mengolah ulang dataset menurunkan trust_status (app/ingestion/core_processor.py)."""
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import ApiKey, Batch, Dataset
from app.security.api_key import hash_key
from app.services.trash import restore_batch, trash_batch

client = TestClient(app)
CSV = b"order_id,tanggal,qty,harga_satuan,subtotal,status\nA1,2026-10-01,2,5000,10000,selesai\n"


@pytest.fixture(scope="module")
def api_key_header():
    key = f"tal_test_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(ApiKey(name="Trust Reset Test Key", key_hash=hash_key(key),
                  key_prefix=key[:12], status="active"))
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {key}"}


def _upload_trusted_dataset(headers):
    tag = uuid.uuid4().hex[:8]
    r = client.post(
        "/ingest/upload",
        headers=headers,
        data={"business_name": f"TR Biz {tag}", "business_category": "lainnya",
              "source_name": f"TR Src {tag}", "dataset_name": f"TR DS {tag}"},
        files={"file": ("tr.csv", CSV, "text/csv")},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "success", r.json().get("error_message")
    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.name == f"TR DS {tag}").first()
        ds.trust_status = "TRUSTED"
        db.commit()
        batch = db.query(Batch).filter(Batch.dataset_id == ds.id).first()
        return ds.id, batch.id
    finally:
        db.close()


def _status(dataset_id):
    db = SessionLocal()
    try:
        return db.get(Dataset, dataset_id).trust_status
    finally:
        db.close()


def test_trashing_a_batch_drops_trust(api_key_header):
    ds_id, batch_id = _upload_trusted_dataset(api_key_header)
    assert _status(ds_id) == "TRUSTED"
    db = SessionLocal()
    try:
        trash_batch(db, db.get(Batch, batch_id), deleted_by="tes")
    finally:
        db.close()
    assert _status(ds_id) == "INGESTED"


def test_restoring_a_batch_drops_trust(api_key_header):
    ds_id, batch_id = _upload_trusted_dataset(api_key_header)
    db = SessionLocal()
    try:
        trash_batch(db, db.get(Batch, batch_id), deleted_by="tes")
    finally:
        db.close()
    db = SessionLocal()
    try:
        ds = db.get(Dataset, ds_id)
        ds.trust_status = "TRUSTED"
        db.commit()
        restore_batch(db, db.get(Batch, batch_id))
    finally:
        db.close()
    assert _status(ds_id) == "INGESTED"