"""
Tes pintu masuk Eksperimen (app/ingestion/lab_inbox.py).

Jalankan (Postgres & MinIO tes harus hidup lewat Docker):
    pytest tests/test_lab_inbox.py -v
"""
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import ApiKey, Batch, Dataset, LabEntry, Project
from app.security.api_key import hash_key

client = TestClient(app)

CSV = b"order_id,customer,total\n1,Andi,1000\n2,Budi,2000\n"


@pytest.fixture(scope="module")
def api_key_header():
    plaintext_key = f"tal_test_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="Lab Inbox Test Key",
            key_hash=hash_key(plaintext_key),
            key_prefix=plaintext_key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {plaintext_key}"}


def _names():
    tag = uuid.uuid4().hex[:8]
    return f"Lab Biz {tag}", f"Lab Src {tag}", f"Lab DS {tag}"


def _upload(headers, names, content=CSV):
    biz, src, ds = names
    return client.post(
        "/ingest/upload",
        headers=headers,
        data={
            "business_name": biz,
            "business_category": "lainnya",
            "source_name": src,
            "dataset_name": ds,
        },
        files={"file": ("lab_inbox.csv", content, "text/csv")},
    )


def _upload_ok(headers, names):
    r = _upload(headers, names)
    assert r.status_code == 201
    assert r.json()['status'] == 'success', r.json().get('error_message')


def _dataset_id(dataset_name):
    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.name == dataset_name).first()
        return ds.id if ds else None
    finally:
        db.close()


def _entry_count(dataset_name):
    db = SessionLocal()
    try:
        return (
            db.query(LabEntry)
            .join(Dataset, Dataset.id == LabEntry.dataset_id)
            .filter(Dataset.name == dataset_name)
            .count()
        )
    finally:
        db.close()


def test_upload_creates_one_lab_entry(api_key_header):
    names = _names()
    r = _upload(api_key_header, names)
    assert r.status_code == 201
    assert r.json()["status"] == "success"
    assert _entry_count(names[2]) == 1

    # Entri terlihat lewat API yang dipakai halaman Eksperimen
    ds_id = str(_dataset_id(names[2]))
    listed = client.get("/lab-entries").json()
    match = [e for e in listed if e["dataset_id"] == ds_id]
    assert len(match) == 1
    assert match[0]["name"] == f"Data masuk: {names[2]}"
    assert match[0]["business_name"] == names[0]


def test_same_dataset_twice_keeps_one_entry_but_two_batches(api_key_header):
    names = _names()
    _upload_ok(api_key_header, names)
    _upload_ok(api_key_header, names)

    assert _entry_count(names[2]) == 1
    db = SessionLocal()
    try:
        batches = db.query(Batch).filter(Batch.dataset_id == _dataset_id(names[2])).count()
    finally:
        db.close()
    assert batches == 2


def test_failed_upload_creates_no_lab_entry(api_key_header):
    names = _names()
    _upload(api_key_header, names, content=b"")  # data kosong -> batch gagal / ditolak
    assert _entry_count(names[2]) == 0


def test_promoted_dataset_does_not_reappear_in_lab(api_key_header):
    names = _names()
    _upload_ok(api_key_header, names)
    ds_id = _dataset_id(names[2])

    # Simulasi "Promosikan": entri staging dihapus, Project dibuat dengan dataset yang sama
    db = SessionLocal()
    try:
        db.query(LabEntry).filter(LabEntry.dataset_id == ds_id).delete()
        db.add(Project(name=f"Proyek {names[2]}", tier="laboratorium", dataset_id=ds_id))
        db.commit()
    finally:
        db.close()

    _upload_ok(api_key_header, names)
    assert _entry_count(names[2]) == 0


def test_lab_inbox_failure_does_not_break_ingest(api_key_header, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("simulasi kegagalan Eksperimen")

    monkeypatch.setattr("app.ingestion.lab_inbox.ensure_lab_entry", boom)

    names = _names()
    r = _upload(api_key_header, names)
    assert r.status_code == 201
    assert r.json()["status"] == "success"  # ingest tetap sukses
    assert _entry_count(names[2]) == 0