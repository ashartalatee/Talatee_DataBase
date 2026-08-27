import uuid
from datetime import datetime

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
    total_records: int


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    status: str
    created_at: datetime
