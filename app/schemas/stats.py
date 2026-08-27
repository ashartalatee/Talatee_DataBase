from pydantic import BaseModel


class SourceBreakdownItem(BaseModel):
    source_id: str
    source_name: str
    total_records: int


class RecentBatchItem(BaseModel):
    id: str
    dataset_name: str
    source_name: str
    filename: str
    status: str
    records_saved: int
    started_at: str


class OverviewStatsOut(BaseModel):
    total_records: int
    total_datasets: int
    total_sources: int
    total_batches: int
    total_storage_bytes: int
    data_by_source: list[SourceBreakdownItem]
    recent_batches: list[RecentBatchItem]
