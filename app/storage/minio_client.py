"""
Wrapper tipis di atas MinIO SDK. Semua akses raw storage HARUS lewat modul ini —
tidak ada bagian lain dari aplikasi yang boleh bicara langsung ke `minio.Minio`.
"""
import io

from minio import Minio

from app.config import settings

_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def ensure_bucket() -> None:
    """Buat bucket kalau belum ada. Dipanggil otomatis di setiap upload_file()."""
    if not _client.bucket_exists(settings.minio_bucket):
        _client.make_bucket(settings.minio_bucket)


def upload_file(
    storage_path: str, data: bytes, content_type: str = "application/octet-stream"
) -> None:
    """Upload bytes ke MinIO di path tertentu. Raw file bersifat immutable —
    caller (IngestionEngine) yang bertanggung jawab memastikan storage_path
    selalu unik per batch, supaya tidak pernah menimpa file lama."""
    ensure_bucket()
    _client.put_object(
        settings.minio_bucket,
        storage_path,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def get_file(storage_path: str) -> bytes:
    """Ambil isi file dari MinIO sebagai bytes. Dipakai endpoint download."""
    response = _client.get_object(settings.minio_bucket, storage_path)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_file(storage_path: str) -> None:
    """Hapus PERMANEN satu object dari MinIO. Hanya boleh dipanggil dari
    alur hard-delete (app/services/trash.py) — trash/soft-delete biasa TIDAK
    boleh memanggil ini, karena raw file harus tetap ada supaya batch bisa
    di-restore. remove_object idempotent di sisi MinIO (tidak error kalau
    object sudah tidak ada), jadi aman dipanggil ulang kalau percobaan
    sebelumnya gagal di tengah jalan."""
    _client.remove_object(settings.minio_bucket, storage_path)


def ping() -> None:
    """Cek koneksi ke MinIO tanpa mengubah apa pun (status kesehatan Showcase)."""
    _client.bucket_exists(settings.minio_bucket)
