"""Daftar Clients dan Datasets membawa status kepercayaan."""
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
    db.add(
        ApiKey(
            name="Badge Test Key",
            key_hash=hash_key(key),
            key_prefix=key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {key}"}


def _business(name):
    items = [b for b in client.get("/businesses").json() if b["name"] == name]
    assert len(items) == 1
    return items[0]


def test_business_list_counts_trusted_datasets_and_datasets_list_has_status(api_key_header):
    tag = uuid.uuid4().hex[:8]
    r = client.post(
        "/ingest/upload",
        headers=api_key_header,
        data={
            "business_name": f"BT Biz {tag}",
            "business_category": "lainnya",
            "source_name": f"BT Src {tag}",
            "dataset_name": f"BT DS {tag}",
        },
        files={"file": ("bt.csv", CSV, "text/csv")},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "success", r.json().get("error_message")

    biz = _business(f"BT Biz {tag}")
    assert biz["total_datasets"] == 1
    assert biz["trusted_datasets"] == 0

    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.name == f"BT DS {tag}").first()
        ds.trust_status = "TRUSTED"
        db.commit()
    finally:
        db.close()

    assert _business(f"BT Biz {tag}")["trusted_datasets"] == 1

    mine = [d for d in client.get("/datasets").json() if d["name"] == f"BT DS {tag}"]
    assert len(mine) == 1
    assert mine[0].get("trust_status") == "TRUSTED"
