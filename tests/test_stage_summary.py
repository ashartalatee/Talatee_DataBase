"""Tes /stage/summary: Panggung hanya boleh memuat data bisnis demo yang TRUSTED.

Tes ini memakai database yang sama dengan tes lain (SessionLocal), jadi memakai nama unik
dan membersihkan datanya sendiri. Sesi dashboard di-override karena yang diuji adalah isi
ringkasannya, bukan login.
"""
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import Batch, Business, Connector, CoreTransaction, Dataset, Source
from app.security.dashboard_session import require_dashboard_session

client = TestClient(app)


@pytest.fixture(autouse=True)
def _session_override():
    app.dependency_overrides[require_dashboard_session] = lambda: "tester"
    yield
    app.dependency_overrides.pop(require_dashboard_session, None)


def _build(db, tag, *, demo, trust, category, source_name, subtotal):
    biz = Business(name=f"Biz-{tag}", category="lainnya", status="active", is_demo=demo)
    db.add(biz)
    db.flush()
    src = Source(business_id=biz.id, name=source_name, type="file_upload", status="active")
    db.add(src)
    db.flush()
    con = Connector(source_id=src.id, name="tes", type="file_upload_csv", config={}, status="active")
    ds = Dataset(source_id=src.id, name=f"ds-{tag}", trust_status=trust)
    db.add_all([con, ds])
    db.flush()
    batch = Batch(dataset_id=ds.id, connector_id=con.id, status="success", records_received=1, records_saved=1, records_failed=0)
    db.add(batch)
    db.flush()
    db.add(
        CoreTransaction(
            dataset_id=ds.id, batch_id=batch.id, order_id=f"O-{tag}", transaction_date=date.today(),
            product_name="P", category=category, qty=1, unit_price=subtotal, subtotal=subtotal,
            status_raw="completed", is_revenue=True,
        )
    )
    db.commit()
    return biz.id, ds.id


def _cleanup(db, biz_ids, ds_ids):
    db.query(CoreTransaction).filter(CoreTransaction.dataset_id.in_(ds_ids)).delete(synchronize_session=False)
    db.commit()
    for bid in biz_ids:
        biz = db.get(Business, bid)
        if biz:
            db.delete(biz)
    db.commit()


def test_summary_shape():
    r = client.get("/stage/summary")
    assert r.status_code == 200
    j = r.json()
    assert len(j["trend"]) == 30
    assert set(j["flow"]) == {"file", "batch", "trust", "question", "answer"}
    assert j["hermes_connected"] is False


def test_summary_only_trusted_demo_data():
    tag = uuid.uuid4().hex[:8]
    db = SessionLocal()
    biz_ids, ds_ids = [], []
    try:
        for kwargs in (
            dict(demo=True, trust="TRUSTED", category=f"KatDemo-{tag}", source_name=f"SrcDemo-{tag}", subtotal=12345),
            dict(demo=True, trust="VALIDATING", category=f"KatBelum-{tag}", source_name=f"SrcBelum-{tag}", subtotal=111),
            dict(demo=False, trust="TRUSTED", category=f"KatKlien-{tag}", source_name=f"SrcKlien-{tag}", subtotal=999999),
        ):
            b, d = _build(db, uuid.uuid4().hex[:6], **kwargs)
            biz_ids.append(b)
            ds_ids.append(d)

        j = client.get("/stage/summary").json()
        cats = {c["name"]: c["value"] for c in j["categories"]}
        chans = {c["name"]: c["value"] for c in j["channels"]}

        assert cats[f"KatDemo-{tag}"] == 12345
        assert chans[f"SrcDemo-{tag}"] == 12345
        # data demo yang belum TRUSTED tidak dihitung sebagai omzet
        assert f"KatBelum-{tag}" not in cats and f"SrcBelum-{tag}" not in chans
        # data bisnis non-demo tidak boleh bocor ke Panggung
        assert f"KatKlien-{tag}" not in cats and f"SrcKlien-{tag}" not in chans
    finally:
        _cleanup(db, biz_ids, ds_ids)
        db.close()
