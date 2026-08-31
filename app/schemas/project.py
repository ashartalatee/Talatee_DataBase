import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.project import PROJECT_TIERS


class ChecklistItem(BaseModel):
    label: str
    done: bool = False


def _validate_tier(v: str) -> str:
    if v not in PROJECT_TIERS:
        raise ValueError(f"tier harus salah satu dari: {', '.join(sorted(PROJECT_TIERS))}")
    return v


class ProjectCreate(BaseModel):
    name: str
    tier: str = "laboratorium"
    status_note: Optional[str] = None
    description: Optional[str] = None
    checklist: Optional[list[ChecklistItem]] = None
    repo_url: Optional[str] = None
    deploy_target: Optional[str] = None
    business_id: Optional[uuid.UUID] = None

    _validate_tier = field_validator("tier")(_validate_tier)


class ProjectUpdate(BaseModel):
    """Semua field opsional — buat PATCH parsial (misal cuma ganti tier)."""

    name: Optional[str] = None
    tier: Optional[str] = None
    status_note: Optional[str] = None
    description: Optional[str] = None
    checklist: Optional[list[ChecklistItem]] = None
    repo_url: Optional[str] = None
    deploy_target: Optional[str] = None
    business_id: Optional[uuid.UUID] = None

    @field_validator("tier")
    @classmethod
    def validate_tier_optional(cls, v):
        if v is None:
            return v
        return _validate_tier(v)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tier: str
    status_note: Optional[str] = None
    description: Optional[str] = None
    checklist: Optional[list[ChecklistItem]] = None
    repo_url: Optional[str] = None
    deploy_target: Optional[str] = None
    business_id: Optional[uuid.UUID] = None
    # Diisi manual di route (bukan lewat from_attributes) kalau business_id
    # terisi — supaya frontend bisa tampilkan jumlah records asli tanpa
    # request terpisah.
    business_name: Optional[str] = None
    business_total_records: Optional[int] = None
    created_at: datetime
    updated_at: datetime
