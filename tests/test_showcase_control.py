"""Tes kendali demo Panggung: hanya menyentuh bisnis demo, lewat jalur dan aturan trust yang asli.

Memakai database dan MinIO yang sama dengan tes lain (SessionLocal), jadi memakai nama unik dan
membersihkan datanya sendiri. Penentuan bisnis demo di-patch ke bisnis buatan tes supaya tidak
bergantung pada bisnis demo lain yang mungkin ada di database tes.
"""
import random
import socket
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.routes import showcase_control as sc
from app.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import Business, CoreTransaction, Dataset, Source
from app.security.dashboard_session import require_dashboard_session
from app.services import demo_data

client = TestClient(app)


@pytest.fixture(autouse=True)
def _session_override():
    app.dependency_overrides[require_dashboard_session] = lambda: "tester"
    yield
    app.dependency_overrides.pop(require_dashboard_session, None)


@pytest.fixture
def storage_up():
    """Lewati tes yang butuh penyimpanan (MinIO) bila endpoint tes tidak terjangkau, tanpa menunggu retry panjang."""
    host, _, port = settings.minio_endpoint.partition(":")
    try:
        socket.create_connection((host, int(port or 9000)), timeout=1).close()
    except OSError:
        pytest.skip(f"MinIO tes ({settings.minio_endpoint}) tidak terjangkau: nyalakan dulu, lalu ulangi.")


@pytest.fixture
def demo_business(monkeypatch):
    tag = uuid.uuid4().hex[:8]
    db = SessionLocal()
    biz = Business(name=f"Demo-{tag}", category="marketplace", status="active", is_demo=True)
    db.add(biz)
    db.commit()
    bid = biz.id
    monkeypatch.setattr(sc, "_demo_business", lambda session: session.get(Business, bid))
    yield bid
    try:
        client.post("/showcase/reset", json={"confirm": True})  # purge sisa data lewat jalur resmi
        row = db.get(Business, bid)
        if row is not None:
            db.delete(row)
            db.commit()
    finally:
        db.close()


def test_demo_data_is_valid_and_unique():
    rng = random.Random(1)
    data, revenue, completed = demo_data.make_batch_csv(rng, 12)
    lines = data.decode().strip().splitlines()
    assert lines[0].split(",") == demo_data.COLUMNS
    assert len(lines) == 13 and revenue >= 0 and completed <= 12
    other, _, _ = demo_data.make_batch_csv(random.Random(1), 12)
    ids = {l.split(",")[0] for l in lines[1:]}
    assert not ids & {l.split(",")[0] for l in other.decode().strip().splitlines()[1:]}  # tidak bentrok antar batch


def test_reset_requires_confirm(demo_business):
    assert client.post("/showcase/reset", json={"confirm": False}).status_code == 400


def test_trigger_makes_trusted_data_and_reset_spares_real_business(demo_business, storage_up):
    db = SessionLocal()
    real = Business(name=f"Klien-{uuid.uuid4().hex[:8]}", category="lainnya", status="active", is_demo=False)
    db.add(real)
    db.commit()
    real_src = Source(business_id=real.id, name="Kasir Klien", type="file_upload", status="active")
    db.add(real_src)
    db.commit()
    real_src_id, real_id = real_src.id, real.id
    try:
        r = client.post("/showcase/simulator/trigger", json={"fast": True, "channel": "Shopee", "orders": 8})
        assert r.status_code == 200, r.text
        result = r.json()["results"][0]
        assert result["ok"] and result["trust_status"] == "TRUSTED"

        ds = db.query(Dataset).join(Source, Dataset.source_id == Source.id).filter(Source.business_id == demo_business).one()
        db.refresh(ds)
        assert ds.trust_status == "TRUSTED"
        assert db.query(CoreTransaction).filter(CoreTransaction.dataset_id == ds.id).count() > 0

        preview = client.get("/showcase/reset/preview").json()
        assert preview["sources"] == 1 and preview["transactions"] > 0

        assert client.post("/showcase/reset", json={"confirm": True}).status_code == 200
        db.expire_all()
        assert db.query(Source).filter(Source.business_id == demo_business).count() == 0
        assert db.get(Business, demo_business) is not None  # bisnis demo tetap ada
        assert db.get(Source, real_src_id) is not None      # data bisnis asli tidak tersentuh
    finally:
        row = db.get(Source, real_src_id)
        if row is not None:
            db.delete(row)
            db.commit()
        biz = db.get(Business, real_id)
        if biz is not None:
            db.delete(biz)
            db.commit()
        db.close()


def test_upload_without_promote_stays_validating(demo_business, storage_up):
    data, _, _ = demo_data.make_batch_csv(random.Random(5), 6)
    r = client.post("/showcase/demo/upload", files={"file": ("tes.csv", data)}, data={"promote": "false"})
    assert r.status_code == 200, r.text
    assert r.json()["results"][0]["trust_status"] == "VALIDATING"


def test_content_digest_depends_only_on_content():
    assert sc._content_digest(b"a,b\n1,2") == sc._content_digest(b"a,b\n1,2")
    assert sc._content_digest(b"a,b\n1,2") != sc._content_digest(b"a,b\n1,3")


def test_upload_same_content_twice_is_rejected(demo_business, storage_up, monkeypatch):
    monkeypatch.setattr(sc, "STEP_DELAY_S", 0)
    data, _, _ = demo_data.make_batch_csv(random.Random(11), 6)
    other, _, _ = demo_data.make_batch_csv(random.Random(12), 6)

    def send(name, content):
        return client.post("/showcase/demo/upload", files={"file": (name, content, "text/csv")}, data={"promote": "false"})

    assert send("pertama.csv", data).status_code == 200
    again = send("nama-lain.csv", data)  # isi sama, nama beda: tetap ditolak
    assert again.status_code == 409
    assert "isi yang sama" in again.json()["detail"]
    assert send("berbeda.csv", other).status_code == 200  # isi beda: lolos

    db = SessionLocal()
    try:
        n = db.query(Dataset).join(Source, Dataset.source_id == Source.id).filter(Source.business_id == demo_business).count()
    finally:
        db.close()
    assert n == 2  # file yang ditolak tidak membuat dataset
