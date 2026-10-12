"""Skema respons GET /stage/summary (kontrak yang sama dengan mock di dashboard/src/pages/useStageData.js)."""
from pydantic import BaseModel


class FlowCount(BaseModel):
    count: int = 0
    last: int | None = None  # epoch milidetik


class FlowTrust(BaseModel):
    INGESTED: int = 0
    VALIDATING: int = 0
    NEEDS_REVIEW: int = 0
    TRUSTED: int = 0
    last: int | None = None


class StageFlow(BaseModel):
    file: FlowCount
    batch: FlowCount
    trust: FlowTrust
    question: FlowCount
    answer: FlowCount


class TrendDay(BaseModel):
    d: str
    rev: float
    ord: int


class NameValue(BaseModel):
    name: str
    value: float


class StockItem(BaseModel):
    name: str
    stok: int


class HermesItem(BaseModel):
    q: str
    a: str
    sources: list[str] = []


class FeedItem(BaseModel):
    t: int
    text: str
    tone: str  # "g" | "b" | "y"


class StageSummaryOut(BaseModel):
    flow: StageFlow
    trend: list[TrendDay]
    categories: list[NameValue]
    channels: list[NameValue]
    low_stock: list[StockItem] = []
    hermes: list[HermesItem] = []
    feed: list[FeedItem]
    # False sampai log Hermes tersimpan di backend; Panggung menampilkan "Belum tersambung".
    hermes_connected: bool = False