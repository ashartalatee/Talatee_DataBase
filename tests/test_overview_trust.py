"""Overview memisahkan dataset terpercaya dan belum (app/api/routes/stats.py)."""
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import ApiKey, Dataset
from app.security.api_key import hash_key

client = TestClient(app)
CSV = b"order_id,tanggal,qty,harga_satuan,subtotal,status\nA1,2026-10-01,2,5000,10000,selesai\n"


@pytest.fixture(scope="module")
def api_key_header():
    key = f"tal_test_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(ApiKey(name="Overview Trust Test Key", key_hash=hash_key(key),
                  key_prefix=key[:12], status="active"))
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {key}"}


def _overview():
    r = client.get("/stats/overview")
    assert r.status_code == 200
    return r.json()


def test_overview_separates_trusted_and_untrusted_datasets(api_key_header):
    before = _overview()
    tag = uuid.uuid4().hex[:8]
    r = client.post(
        "/ingest/upload",
        headers=api_key_header,
        data={"business_name": f"OV Biz {tag}", "business_category": "lainnya",
              "source_name": f"OV Src {tag}", "dataset_name": f"OV DS {tag}"},
        files={"file": ("ov.csv", CSV, "text/csv")},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "success", r.json().get("error_message")

    mid = _overview()
    assert mid["untrusted_datasets"] == before["untrusted_datasets"] + 1
    assert mid["trusted_datasets"] == before["trusted_datasets"]

    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.name == f"OV DS {tag}").first()
        ds.trust_status = "TRUSTED"
        db.commit()
    finally:
        db.close()

    after = _overview()
    assert after["trusted_datasets"] == before["trusted_datasets"] + 1
    assert after["untrusted_datasets"] == before["untrusted_datasets"]