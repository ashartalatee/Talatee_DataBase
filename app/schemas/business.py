import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BusinessListItemOut(BaseModel):
    """Item ringkas untuk GET /businesses — dengan agregasi jumlah source/dataset/records."""

    id: uuid.UUID
    name: str
    category: str
    status: str
    created_at: datetime
    total_sources: int
    total_datasets: int
    trusted_datasets: int = 0
    total_records: int
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    status: str
    created_at: datetime
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
