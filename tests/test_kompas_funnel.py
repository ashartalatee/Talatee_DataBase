"""
Test untuk penghitung corong di bagian Arah (app/api/routes/kompas_funnel.py
+ app/models/kompas_funnel.py + migrasi s7a9c1e3f568).

Pakai Postgres SUNGGUHAN, sama seperti test lain di folder ini (upsert
`ON CONFLICT` itu khusus PostgreSQL, jadi tidak bisa diuji dengan SQLite).
Postgres harus jalan lewat `docker compose up -d`, dan migrasi harus sudah
diterapkan (`python -m alembic upgrade head`).

Login dashboard di-override per test dengan username UNIK (funnel_test_<hex>),
jadi data asli milik 'admin' tidak pernah tersentuh. Baris milik username uji
dihapus lagi setelah tiap test selesai.

Jalankan:
    pytest tests/test_kompas_funnel.py -v
"""
import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.main import app
from app.models.kompas_funnel import FUNNEL_STREAMS, MAX_COUNT, KompasFunnel
from app.security.dashboard_session import DISABLE_LOGIN_FOR_LOCAL_DEV, require_dashboard_session

client = TestClient(app)


@pytest.fixture
def funnel_user():
    """Panggil `use()` untuk masuk sebagai pengguna uji baru (atau nama tertentu)."""
    names = []

    def use(name=None):
        name = name or f"funnel_test_{secrets.token_hex(4)}"
        names.append(name)
        app.dependency_overrides[require_dashboard_session] = lambda: name
        return name

    yield use

    app.dependency_overrides.pop(require_dashboard_session, None)
    db = SessionLocal()
    try:
        db.query(KompasFunnel).filter(KompasFunnel.username.in_(names)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _bump(stream, stage, delta, c=client):
    return c.post(f"/kompas/funnel/{stream}/{stage}", json={"delta": delta})


@pytest.mark.skipif(DISABLE_LOGIN_FOR_LOCAL_DEV, reason="Login dashboard sedang dimatikan untuk dev lokal")
def test_funnel_requires_login():
    """Tanpa cookie sesi, baca maupun ubah harus ditolak 401."""
    assert client.get("/kompas/funnel").status_code == 401
    assert _bump("klien", 0, 1).status_code == 401


def test_funnel_starts_empty(funnel_user):
    funnel_user()
    r = client.get("/kompas/funnel")
    assert r.status_code == 200
    assert r.json() == {s: [0, 0, 0, 0] for s in FUNNEL_STREAMS}


def test_funnel_increase_persists(funnel_user):
    funnel_user()
    assert _bump("klien", 0, 1).json() == {"stream": "klien", "stage": 0, "count": 1}
    assert _bump("klien", 0, 1).json()["count"] == 2
    assert _bump("klien", 3, 1).json()["count"] == 1

    data = client.get("/kompas/funnel").json()
    assert data["klien"] == [2, 0, 0, 1]
    assert data["kerja"] == [0, 0, 0, 0]


def test_funnel_never_below_zero(funnel_user):
    funnel_user()
    # Baris belum ada dan langsung dikurangi: tetap 0, bukan error dan bukan minus.
    r = _bump("kerja", 1, -1)
    assert r.status_code == 200
    assert r.json()["count"] == 0

    _bump("kerja", 1, 1)
    _bump("kerja", 1, 1)
    assert _bump("kerja", 1, -1).json()["count"] == 1
    assert _bump("kerja", 1, -1).json()["count"] == 0
    assert _bump("kerja", 1, -1).json()["count"] == 0


def test_funnel_caps_at_max_count(funnel_user):
    name = funnel_user()
    db = SessionLocal()
    db.add(KompasFunnel(username=name, stream="produk", stage=2, count=MAX_COUNT))
    db.commit()
    db.close()

    assert _bump("produk", 2, 1).json()["count"] == MAX_COUNT


@pytest.mark.parametrize("stream,stage", [("tidak_ada", 0), ("klien", 4), ("klien", -1)])
def test_funnel_rejects_unknown_stream_or_stage(funnel_user, stream, stage):
    funnel_user()
    assert _bump(stream, stage, 1).status_code == 404


def test_funnel_rejects_non_numeric_stage(funnel_user):
    funnel_user()
    assert _bump("klien", "abc", 1).status_code == 422


@pytest.mark.parametrize("delta", [0, 2, -2, 10])
def test_funnel_rejects_invalid_delta(funnel_user, delta):
    funnel_user()
    assert _bump("klien", 0, delta).status_code == 422


def test_funnel_requires_delta_body(funnel_user):
    funnel_user()
    assert client.post("/kompas/funnel/klien/0").status_code == 422


def test_funnel_is_separate_per_user(funnel_user):
    funnel_user("funnel_test_a_" + secrets.token_hex(3))
    _bump("klien", 0, 1)
    _bump("klien", 0, 1)

    name_b = "funnel_test_b_" + secrets.token_hex(3)
    funnel_user(name_b)
    assert client.get("/kompas/funnel").json()["klien"] == [0, 0, 0, 0]
    assert _bump("klien", 0, 1).json()["count"] == 1


def test_funnel_concurrent_bumps_do_not_overwrite_each_other(funnel_user):
    """Upsert atomik: banyak permintaan bersamaan pada baris yang BELUM ada
    tidak boleh menghilangkan hitungan (tidak ada lost update)."""
    name = funnel_user()
    n = 8

    def one(_):
        with TestClient(app) as c:
            return _bump("konten", 0, 1, c=c).status_code

    with ThreadPoolExecutor(max_workers=n) as pool:
        codes = list(pool.map(one, range(n)))

    assert codes == [200] * n
    assert client.get("/kompas/funnel").json()["konten"][0] == n


@pytest.mark.parametrize(
    "stage,count",
    [(0, -1), (4, 0), (-1, 0)],
)
def test_db_constraints_block_bad_rows(funnel_user, stage, count):
    """Pengaman di level database (dari migrasi), terlepas dari API."""
    name = funnel_user()
    db = SessionLocal()
    try:
        db.add(KompasFunnel(username=name, stream="klien", stage=stage, count=count))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()
