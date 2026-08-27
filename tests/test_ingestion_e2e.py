"""
Test end-to-end Langkah 6: upload -> cek MinIO -> cek Postgres -> cek API lain.

Jalankan dengan (Postgres & MinIO harus jalan lewat `docker compose up -d`):
    pytest tests/test_ingestion_e2e.py -v

PENTING: test ini pakai Postgres & MinIO SUNGGUHAN (bukan mock/in-memory),
sesuai isi ARCHITECTURE.md ("test end-to-end: upload -> cek MinIO -> cek
Postgres"). Setiap kali dijalankan akan menambah data baru — ini SESUAI
DESAIN, karena raw data tidak pernah di-overwrite (Prinsip Inti #2), jadi
run berkali-kali menghasilkan batch baru terus, bukan bug.

Sejak fitur Auth (API key) ditambahkan, endpoint /ingest/upload butuh header
Authorization — fixture `api_key_header` generate 1 API key baru khusus test
ini setiap kali test session dijalankan (lihat app/security/api_key.py).
"""
import hashlib
import secrets

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import ApiKey, Batch
from app.models import File as FileModel
from app.security.api_key import hash_key
from app.storage.minio_client import get_file

client = TestClient(app)

SAMPLE_CSV = b"order_id,customer,total\n1,Andi,1000\n2,Budi,2000\n3,Citra,3000\n"


@pytest.fixture(scope="module")
def api_key_header():
    """Generate 1 API key baru khusus untuk sesi test ini."""
    plaintext_key = f"tal_test_{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    db.add(
        ApiKey(
            name="E2E Test Key",
            key_hash=hash_key(plaintext_key),
            key_prefix=plaintext_key[:12],
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {plaintext_key}"}


def test_upload_requires_api_key():
    """Upload TANPA header Authorization harus ditolak 401, bukan diproses."""
    response = client.post(
        "/ingest/upload",
        data={
            "business_name": "Should Not Exist",
            "source_name": "S",
            "dataset_name": "D",
        },
        files={"file": ("x.csv", SAMPLE_CSV, "text/csv")},
    )
    assert response.status_code == 401


def test_upload_end_to_end(api_key_header):
    """
    1. Upload file CSV contoh lewat /ingest/upload
    2. Assert response sukses dan berisi batch_id
    3. Assert file benar-benar ada di MinIO di path yang sesuai struktur
    4. Assert row batches dan files di Postgres sesuai (status success, checksum cocok)
    5. Assert GET /datasets/{id} menunjukkan dataset baru dengan record count yang benar
    """
    # 1 & 2: upload, assert sukses + ada batch_id
    files = {"file": ("e2e_test.csv", SAMPLE_CSV, "text/csv")}
    data = {
        "business_name": "E2E Test Business",
        "business_category": "lainnya",
        "source_name": "E2E Test Source",
        "dataset_name": "E2E Test Dataset",
    }
    response = client.post("/ingest/upload", data=data, files=files, headers=api_key_header)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert "id" in body
    batch_id = body["id"]
    dataset_id = body["dataset_id"]

    # 3: file benar-benar ada di MinIO, path sesuai struktur raw/{slug}/..., isi identik
    db = SessionLocal()
    file_row = db.query(FileModel).filter(FileModel.batch_id == batch_id).first()
    assert file_row is not None
    assert file_row.storage_path.startswith("raw/e2e_test_business/e2e_test_source/")
    assert file_row.filename == "e2e_test.csv"

    minio_data = get_file(file_row.storage_path)
    assert minio_data == SAMPLE_CSV

    # 4: row batches & files di Postgres sesuai — status success, checksum cocok
    batch_row = db.query(Batch).filter(Batch.id == batch_id).first()
    assert batch_row is not None
    assert batch_row.status == "success"
    assert batch_row.records_saved == 3

    expected_checksum = hashlib.sha256(SAMPLE_CSV).hexdigest()
    assert file_row.checksum == expected_checksum
    db.close()

    # 5: GET /datasets/{id} menunjukkan dataset baru dengan record count benar
    ds_response = client.get(f"/datasets/{dataset_id}")
    assert ds_response.status_code == 200
    ds_body = ds_response.json()
    assert ds_body["name"] == "E2E Test Dataset"
    assert len(ds_body["batches"]) >= 1
    assert ds_body["batches"][0]["records_saved"] == 3


def test_upload_same_file_twice_creates_two_batches(api_key_header):
    """
    Prinsip Inti #2: raw data tidak pernah di-overwrite. Upload file yang SAMA
    PERSIS dua kali harus menghasilkan DUA batch terpisah dengan storage_path
    berbeda (bukan 1 batch yang di-overwrite), walau checksum-nya identik.
    """
    data = {
        "business_name": "E2E Duplicate Business",
        "business_category": "lainnya",
        "source_name": "E2E Duplicate Source",
        "dataset_name": "E2E Duplicate Dataset",
    }

    r1 = client.post(
        "/ingest/upload", data=data,
        files={"file": ("duplicate_test.csv", SAMPLE_CSV, "text/csv")},
        headers=api_key_header,
    )
    assert r1.status_code == 201
    batch_id_1 = r1.json()["id"]

    r2 = client.post(
        "/ingest/upload", data=data,
        files={"file": ("duplicate_test.csv", SAMPLE_CSV, "text/csv")},
        headers=api_key_header,
    )
    assert r2.status_code == 201
    batch_id_2 = r2.json()["id"]

    assert batch_id_1 != batch_id_2

    db = SessionLocal()
    file1 = db.query(FileModel).filter(FileModel.batch_id == batch_id_1).first()
    file2 = db.query(FileModel).filter(FileModel.batch_id == batch_id_2).first()
    db.close()

    assert file1.storage_path != file2.storage_path
    assert file1.checksum == file2.checksum
