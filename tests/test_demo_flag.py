"""Tes M1a: penanda demo, pengikatan API key ke bisnis, filter include_demo, dan seed demo.

Tes ini memanggil endpoint sungguhan lewat TestClient, jadi kesalahan seperti
impor yang hilang atau join yang salah di query berfilter akan tertangkap.
"""
import importlib.util
import json
import pathlib
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import ApiKey, Batch, Business, Dataset, Source
from app.security.api_key import hash_key

client = TestClient(app)
CSV = b"order_id,tanggal,qty,harga_satuan,subtotal,status\nA1,2026-10-01,2,5000,10000,selesai\n"


# ---------------------------------------------------------------- pembantu

def _tag():
    return uuid.uuid4().hex[:8]


def _make_business(name, is_demo=False):
    db = SessionLocal()
    try:
        b = Business(name=name, category="lainnya", status="active", is_demo=is_demo)
        db.add(b)
        db.commit()
        return b.id
    finally:
        db.close()


def _make_key(business_id=None):
    key = f"tal_test_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    try:
        row = ApiKey(
            name="Demo Flag Test Key",
            key_hash=hash_key(key),
            key_prefix=key[:12],
            status="active",
            business_id=business_id,
        )
        db.add(row)
        db.commit()
        return {"Authorization": f"Bearer {key}"}, row.id
    finally:
        db.close()


def _upload(headers, business_name, suffix):
    data = {
        "source_name": f"Src {suffix}",
        "dataset_name": f"DS {suffix}",
        "business_category": "lainnya",
    }
    if business_name is not None:
        data["business_name"] = business_name
    return client.post(
        "/ingest/upload",
        headers=headers,
        data=data,
        files={"file": ("t.csv", CSV, "text/csv")},
    )


def _business_of_batch(batch_id):
    db = SessionLocal()
    try:
        return (
            db.query(Business.name)
            .join(Source, Source.business_id == Business.id)
            .join(Dataset, Dataset.source_id == Source.id)
            .join(Batch, Batch.dataset_id == Dataset.id)
            .filter(Batch.id == uuid.UUID(str(batch_id)))
            .scalar()
        )
    finally:
        db.close()


def _count_businesses(name):
    db = SessionLocal()
    try:
        return db.query(Business).filter(Business.name == name).count()
    finally:
        db.close()


def _overview(include_demo=False):
    params = {"include_demo": "true"} if include_demo else {}
    r = client.get("/stats/overview", params=params)
    assert r.status_code == 200, r.text
    return r.json()


LIST_PATHS = {
    "datasets": "/datasets",
    "sources": "/sources",
    "lab_entries": "/lab-entries",
}


def _list_text(module, include_demo):
    path = LIST_PATHS[module]
    params = {"include_demo": "true"} if include_demo else {}
    r = client.get(path, params=params)
    assert r.status_code == 200, f"GET {path} {params} -> {r.status_code}: {r.text[:300]}"
    assert isinstance(r.json(), list), f"GET {path} bukan daftar JSON"
    return path, r.text


# ------------------------------------------------- API key terikat ke bisnis

def test_bound_key_cannot_write_to_other_business():
    tag = _tag()
    bound, other = f"Bound {tag}", f"Other {tag}"
    bid = _make_business(bound, True)
    _make_business(other)
    hdr, _ = _make_key(bid)

    r = _upload(hdr, other, tag)
    assert r.status_code == 403, r.text


def test_bound_key_cannot_create_a_new_business():
    tag = _tag()
    bid = _make_business(f"Bound {tag}", True)
    hdr, _ = _make_key(bid)
    new_name = f"Baru {tag}"

    r = _upload(hdr, new_name, tag)
    assert r.status_code == 403, r.text
    assert _count_businesses(new_name) == 0


def test_bound_key_without_name_uses_its_own_business():
    tag = _tag()
    bound = f"Bound {tag}"
    bid = _make_business(bound, True)
    hdr, _ = _make_key(bid)

    r = _upload(hdr, None, tag)
    assert r.status_code == 201, r.text
    assert _business_of_batch(r.json()["id"]) == bound


def test_bound_key_with_its_own_name_is_accepted():
    tag = _tag()
    bound = f"Bound {tag}"
    bid = _make_business(bound, True)
    hdr, _ = _make_key(bid)

    r = _upload(hdr, bound, tag)
    assert r.status_code == 201, r.text
    assert _business_of_batch(r.json()["id"]) == bound


def test_bound_key_is_enforced_on_mixed_upload_route():
    tag = _tag()
    bound, other = f"Bound {tag}", f"Other {tag}"
    bid = _make_business(bound, True)
    _make_business(other)
    hdr, _ = _make_key(bid)

    r = client.post(
        "/ingest/upload/mixed",
        headers=hdr,
        data={"business_name": other, "dataset_name": f"DS {tag}"},
        files={"file": ("t.csv", CSV, "text/csv")},
    )
    assert r.status_code == 403, r.text


def test_duplicate_business_name_is_refused_for_bound_key():
    tag = _tag()
    bound = f"Kembar {tag}"
    bid = _make_business(bound, True)
    _make_business(bound)  # bisnis kedua dengan nama sama
    hdr, _ = _make_key(bid)

    r = _upload(hdr, None, tag)
    assert r.status_code == 409, r.text


def test_legacy_key_still_works_and_still_requires_a_name():
    tag = _tag()
    hdr, _ = _make_key(None)

    ok = _upload(hdr, f"Legacy {tag}", tag)
    assert ok.status_code == 201, ok.text

    missing = _upload(hdr, None, f"{tag}x")
    assert missing.status_code == 422, missing.text


def test_bound_key_is_removed_when_its_business_is_deleted():
    bid = _make_business(f"Cascade {_tag()}", True)
    _, key_id = _make_key(bid)

    db = SessionLocal()
    try:
        db.delete(db.get(Business, bid))
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        assert db.get(ApiKey, key_id) is None
    finally:
        db.close()


# ----------------------------------------------- filter include_demo (daftar)

def test_demo_business_hidden_by_default_and_visible_with_include_demo():
    tag = _tag()
    demo, real = f"Demo {tag}", f"Real {tag}"
    _make_business(demo, True)
    hdr, _ = _make_key(None)

    base_default, base_inc = _overview(), _overview(True)

    r_demo = _upload(hdr, demo, f"{tag}d")
    r_real = _upload(hdr, real, f"{tag}r")
    assert r_demo.status_code == 201, r_demo.text
    assert r_real.status_code == 201, r_real.text
    demo_batch, real_batch = r_demo.json()["id"], r_real.json()["id"]

    # Overview: bisnis demo tidak mengubah angka default, tetapi terhitung bila diminta.
    d, i = _overview(), _overview(True)
    assert d["untrusted_datasets"] == base_default["untrusted_datasets"] + 1
    assert i["untrusted_datasets"] == base_inc["untrusted_datasets"] + 2

    # Daftar bisnis
    names_default = [b["name"] for b in client.get("/businesses").json()]
    assert real in names_default and demo not in names_default
    inc = {b["name"]: b for b in client.get("/businesses", params={"include_demo": "true"}).json()}
    assert inc[demo]["is_demo"] is True
    assert inc[real]["is_demo"] is False

    # Daftar batch
    ids_default = {b["id"] for b in client.get("/batches").json()}
    ids_inc = {b["id"] for b in client.get("/batches", params={"include_demo": "true"}).json()}
    assert real_batch in ids_default and demo_batch not in ids_default
    assert demo_batch in ids_inc and real_batch in ids_inc

    # Daftar dataset, source, dan antrean Eksperimen
    for module in ("datasets", "sources", "lab_entries"):
        _, text_default = _list_text(module, False)
        _, text_inc = _list_text(module, True)
        assert f"{tag}r" in text_default, f"{module}: bisnis nyata harus tampil di daftar default"
        assert f"{tag}d" not in text_default, f"{module}: bisnis demo bocor ke daftar default"
        assert f"{tag}d" in text_inc and f"{tag}r" in text_inc, (
            f"{module}: include_demo harus menyertakan demo"
        )

    # Detail per ID tetap bisa dibuka untuk data demo (dibutuhkan Gudang Data nanti).
    r = client.get(f"/batches/{demo_batch}")
    assert r.status_code == 200, r.text


# ------------------------------------------------------------------- MCP

def test_mcp_server_source_exposes_is_demo_and_does_not_hide_demo():
    """Tes statis (tanpa mengimpor paket `mcp`, yang tidak terpasang di venv aplikasi)."""
    path = pathlib.Path(__file__).resolve().parents[1] / "app" / "mcp" / "server.py"
    text = path.read_text(encoding="utf-8")
    assert '"is_demo"' in text, "list_businesses harus menyertakan penanda is_demo"
    assert "is_demo.is_(False)" not in text, (
        "tool MCP tidak boleh menyembunyikan bisnis demo; Hermes harus bisa memilihnya secara eksplisit"
    )


def _call_tool(tool, **kwargs):
    return getattr(tool, "fn", tool)(**kwargs)


def test_mcp_list_businesses_includes_is_demo_and_demo_is_queryable_explicitly():
    pytest.importorskip("mcp", reason="paket mcp hanya ada di lingkungan server MCP")
    from app.mcp import server as mcp_server

    name = f"Demo MCP {_tag()}"
    _make_business(name, True)

    items = _call_tool(mcp_server.list_businesses)
    mine = [i for i in items if i["business"] == name]
    assert mine, "bisnis demo harus muncul di list_businesses agar Hermes bisa memilihnya"
    assert mine[0]["is_demo"] is True

    res = _call_tool(mcp_server.get_business_summary, business_name=name)
    assert name in json.dumps(res, default=str)


# ------------------------------------------------------------------ seed

def _seed_module():
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"
    spec = importlib.util.spec_from_file_location("seed_demo_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _active_keys(db, business_id):
    return (
        db.query(ApiKey)
        .filter(ApiKey.business_id == business_id, ApiKey.status == "active")
        .count()
    )


def test_seed_demo_is_idempotent_and_rotation_revokes_old_key():
    seed = _seed_module()
    name = f"Seed {_tag()}"
    db = SessionLocal()
    try:
        b1, created = seed.ensure_demo_business(db, name)
        assert created and b1.is_demo is True

        k1 = seed.ensure_demo_key(db, b1)
        assert k1 and k1.startswith("tal_")

        b2, created2 = seed.ensure_demo_business(db, name)
        assert not created2 and b2.id == b1.id
        assert seed.ensure_demo_key(db, b2) is None
        assert _active_keys(db, b1.id) == 1

        k2 = seed.ensure_demo_key(db, b2, rotate=True)
        assert k2 and k2 != k1
        assert _active_keys(db, b1.id) == 1
        revoked = (
            db.query(ApiKey)
            .filter(ApiKey.business_id == b1.id, ApiKey.status == "revoked")
            .count()
        )
        assert revoked == 1
    finally:
        db.close()


def test_seed_demo_key_works_for_upload_and_is_bound():
    seed = _seed_module()
    name = f"Seed {_tag()}"
    db = SessionLocal()
    try:
        business, _ = seed.ensure_demo_business(db, name)
        plaintext = seed.ensure_demo_key(db, business)
    finally:
        db.close()

    hdr = {"Authorization": f"Bearer {plaintext}"}
    r = _upload(hdr, None, _tag())
    assert r.status_code == 201, r.text
    assert _business_of_batch(r.json()["id"]) == name

    r2 = _upload(hdr, f"Lain {_tag()}", _tag())
    assert r2.status_code == 403, r2.text


def test_seed_demo_refuses_existing_non_demo_business():
    seed = _seed_module()
    name = f"Nyata {_tag()}"
    _make_business(name, False)
    db = SessionLocal()
    try:
        with pytest.raises(RuntimeError):
            seed.ensure_demo_business(db, name)
    finally:
        db.close()


def test_seed_demo_adopt_requires_confirmation():
    seed = _seed_module()
    name = f"Adopsi {_tag()}"
    _make_business(name, False)

    db = SessionLocal()
    try:
        b, changed = seed.adopt_business(db, name, confirm=lambda biz: False)
        assert not changed and b.is_demo is False
        b, changed = seed.adopt_business(db, name, confirm=lambda biz: True)
        assert changed and b.is_demo is True
    finally:
        db.close()
