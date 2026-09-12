import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    type: str
    status: str
    created_at: datetime
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
