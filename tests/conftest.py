"""
Pengaman tes: tes HANYA boleh memakai Postgres + MinIO lokal (Docker).
Aplikasi asli tidak diubah; semua penyesuaian hanya berlaku selama pytest.
"""
import os

import pytest

TEST_DB_URL = "postgresql://talatee:talatee@localhost:5434/talatee_test"

# Paksa tes ke infrastruktur lokal (environment variable mengalahkan .env)
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["MINIO_ENDPOINT"] = "localhost:9100"
os.environ["MINIO_ACCESS_KEY"] = "talatee"
os.environ["MINIO_SECRET_KEY"] = "talatee123"
os.environ["MINIO_SECURE"] = "false"


def pytest_sessionstart(session):
    """Hentikan semua tes kalau konfigurasi ternyata mengarah ke cloud."""
    from app.config import settings

    db = settings.database_url
    storage = settings.minio_endpoint
    banned = ("neon.tech", "cloudflarestorage.com", "amazonaws.com")

    if any(b in db for b in banned) or any(b in storage for b in banned):
        raise RuntimeError("DIHENTIKAN: tes mengarah ke database/storage cloud.")
    if "localhost" not in db or not db.endswith("_test"):
        raise RuntimeError("DIHENTIKAN: database tes harus lokal dan berakhiran _test.")


@pytest.fixture(autouse=True)
def _login_palsu_untuk_tes(request):
    """Tes boleh memanggil endpoint dashboard tanpa cookie login.
    Dipasang ulang sebelum tiap tes, dan dilewati untuk tes yang
    memang menguji penolakan tanpa login (nama mengandung 'requires_login')."""
    from app.main import app
    from app.security.dashboard_session import require_dashboard_session

    if "requires_login" in request.node.name:
        app.dependency_overrides.pop(require_dashboard_session, None)
        yield
        return

    app.dependency_overrides[require_dashboard_session] = lambda: "admin"
    yield
    app.dependency_overrides.pop(require_dashboard_session, None)