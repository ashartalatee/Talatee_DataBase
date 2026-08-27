import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.batch import BatchOut


class DatasetListItemOut(BaseModel):
    """Item ringkas untuk GET /datasets: total_records & terakhir diupdate.
    Dibangun manual di route (bukan langsung dari_attributes ORM) karena
    total_records/total_batches hasil agregasi, bukan kolom di tabel."""

    id: uuid.UUID
    source_id: uuid.UUID
    name: str
    description: Optional[str] = None
    updated_at: datetime
    total_records: int
    total_batches: int


class DatasetDetailOut(BaseModel):
    """Detail dataset + riwayat batches — untuk GET /datasets/{id}."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    source_id: uuid.UUID
    name: str
    description: Optional[str] = None
    # Kolom DB bernama "schema", tapi attribute Python-nya "schema_" (kata
    # "schema" reserved di SQLAlchemy Declarative). serialization_alias supaya
    # JSON output tetap pakai key "schema", bukan "schema_".
    schema_: Optional[dict] = Field(default=None, serialization_alias="schema")
    created_at: datetime
    updated_at: datetime
    batches: list[BatchOut] = []
