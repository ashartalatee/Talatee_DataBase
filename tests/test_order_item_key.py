"""Format ekspor toko (tanpa order_id dan status): kunci baris = transaction_ref + produk.

Satu pesanan bisa punya beberapa baris produk, jadi transaction_ref saja tidak
boleh dipakai sebagai kunci dedup (baris produk lain dalam pesanan yang sama
akan hilang). Upload ulang file yang diperbarui harus menimpa baris yang sama
(nilai terbaru menang), bukan menggandakannya.

Catatan: kolom `channel` sengaja tidak dipakai di tes ini supaya yang diuji
hanya kunci baris, bukan aturan channel_guard.
"""
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import ApiKey, CoreTransaction, Dataset
from app.security.api_key import hash_key

client = TestClient(app)

HEADER = "tanggal,waktu,transaction_ref,produk,kategori,qty,harga_satuan,subtotal\n"

# 4 baris: pesanan R1 punya DUA produk (transaction_ref sama, produk beda)
V1 = (
    HEADER
    + "2026-09-11,10:00,R1,Celurit,Peralatan,1,5000,5000\n"
    + "2026-09-11,10:00,R1,Pisau,Peralatan,2,7500,15000\n"
    + "2026-09-11,11:00,R2,Celurit,Peralatan,1,5000,5000\n"
    + "2026-09-11,12:00,R3,Parang,Peralatan,1,9000,9000\n"
).encode()

# Versi diperbarui: R2 berubah (qty 2), ditambah satu baris baru (R4)
V2 = (
    HEADER
    + "2026-09-11,10:00,R1,Celurit,Peralatan,1,5000,5000\n"
    + "2026-09-11,10:00,R1,Pisau,Peralatan,2,7500,15000\n"
    + "2026-09-11,11:00,R2,Celurit,Peralatan,2,5000,10000\n"
    + "2026-09-11,12:00,R3,Parang,Peralatan,1,9000,9000\n"
    + "2026-09-11,13:00,R4,Sabit,Peralatan,1,6000,6000\n"
).encode()


@pytest.fixture(scope="module")
def api_key_header():
    key = f"tal_test_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="Order Item Key Test Key",
            key_hash=hash_key(key),
            key_prefix=key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {key}"}


def _upload(headers, names, content):
    biz, src, ds = names
    r = client.post(
        "/ingest/upload",
        headers=headers,
        data={
            "business_name": biz,
            "business_category": "lainnya",
            "source_name": src,
            "dataset_name": ds,
        },
        files={"file": ("ekspor.csv", content, "text/csv")},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "success", r.json().get("error_message")


def _dataset_id(name):
    db = SessionLocal()
    try:
        return db.query(Dataset).filter(Dataset.name == name).first().id
    finally:
        db.close()


def _process(dataset_id):
    r = client.post(f"/datasets/{dataset_id}/process")
    assert r.status_code == 200, r.text
    return r.json()


def _core_rows(dataset_id):
    db = SessionLocal()
    try:
        return (
            db.query(CoreTransaction)
            .filter(CoreTransaction.dataset_id == dataset_id)
            .all()
        )
    finally:
        db.close()


def test_order_with_two_products_keeps_both_rows_and_reupload_dedups(api_key_header):
    tag = uuid.uuid4().hex[:8]
    names = (f"OK Biz {tag}", f"OK Src {tag}", f"OK DS {tag}")

    # 1. Upload pertama: tidak boleh ada baris yang hilang
    _upload(api_key_header, names, V1)
    ds_id = _dataset_id(names[2])
    s1 = _process(ds_id)
    assert s1["rows_total"] == 4
    assert s1["rows_written"] == 4
    assert s1["duplicate_count"] == 0
    assert len(_core_rows(ds_id)) == 4

    # 2. Upload versi diperbarui ke dataset yang sama: baris lama tergantikan
    _upload(api_key_header, names, V2)
    s2 = _process(ds_id)
    assert s2["rows_total"] == 9  # 4 lama + 5 baru
    assert s2["duplicate_count"] == 4  # 4 baris lama kalah dari versi baru
    assert s2["rows_written"] == 5

    rows = {r.order_id: r for r in _core_rows(ds_id)}
    assert len(rows) == 5
    assert float(rows["R2|Celurit"].subtotal) == 10000  # nilai terbaru menang
    assert "R4|Sabit" in rows  # baris baru ikut masuk
