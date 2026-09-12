import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TrashItemOut(BaseModel):
    """Satu baris di halaman Sampah/Trash — bisa Source, Dataset, atau
    Batch, disatukan lewat field `level` supaya frontend cukup render 1
    daftar campuran diurutkan by deleted_at, bukan 3 daftar terpisah."""

    level: str  # "source" | "dataset" | "batch"
    id: uuid.UUID
    name: str
    context_path: str  # misal "Resto Padang Jaya / Toko Kelontong"
    deleted_at: datetime
    deleted_by: Optional[str] = None


class TrashListOut(BaseModel):
    items: list[TrashItemOut]


class DeletionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    level: str
    entity_id: uuid.UUID
    entity_name: str
    context_path: str
    batches_deleted: int
    files_deleted: int
    records_deleted: int
    reason: Optional[str] = None
    deleted_by: Optional[str] = None
    deleted_at: datetime


class PurgeRequest(BaseModel):
    """Body konfirmasi hapus permanen — confirm_name harus PERSIS sama
    dengan nama entity-nya (dicek di route), supaya tidak ada hapus
    permanen ke-klik tanpa sengaja."""

    confirm_name: str
    reason: Optional[str] = None
