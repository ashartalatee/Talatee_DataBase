import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.project import ChecklistItem


class LabEntryCreate(BaseModel):
    name: str
    note: Optional[str] = None
    checklist: Optional[list[ChecklistItem]] = None
    business_id: Optional[uuid.UUID] = None
    dataset_id: Optional[uuid.UUID] = None


class LabEntryUpdate(BaseModel):
    """Semua field opsional — buat PATCH parsial (misal cuma toggle checklist)."""

    name: Optional[str] = None
    note: Optional[str] = None
    checklist: Optional[list[ChecklistItem]] = None
    business_id: Optional[uuid.UUID] = None
    dataset_id: Optional[uuid.UUID] = None


class LabEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    note: Optional[str] = None
    checklist: Optional[list[ChecklistItem]] = None
    business_id: Optional[uuid.UUID] = None
    business_name: Optional[str] = None
    business_total_records: Optional[int] = None
    dataset_id: Optional[uuid.UUID] = None
    dataset_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
