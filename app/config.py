"""
Konfigurasi aplikasi. Semua nilai dibaca dari environment variable / file .env,
tidak ada nilai sensitif yang di-hardcode di kode.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql://talatee:talatee@localhost:5432/talatee_platform"

    # MinIO / object storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "talatee"
    minio_secret_key: str = "talatee123"
    minio_bucket: str = "talatee-raw"
    minio_secure: bool = False


# Instance singleton, di-import di tempat lain: `from app.config import settings`
settings = Settings()
