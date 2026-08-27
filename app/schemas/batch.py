import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    storage_path: str
    file_size: int
    checksum: str
    uploaded_at: datetime


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    connector_id: uuid.UUID
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    records_received: int
    records_saved: int
    records_failed: int
    error_message: Optional[str] = None


class BatchDetailOut(BatchOut):
    """Detail satu batch + daftar file-nya — dipakai GET /batches/{id}."""

    files: list[FileOut] = []
