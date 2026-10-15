"""Skema respons GET /stage/summary (kontrak yang sama dengan mock di dashboard/src/pages/useStageData.js)."""
from pydantic import BaseModel, Field


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


class EventItem(BaseModel):
    t: int
    kind: str  # "file" | "read" | "clean" | "validate" | "trust" | "insight" | "info"
    text: str
    tone: str = "b"
    batchId: str | None = None


class AgentState(BaseModel):
    status: str = "idle"  # "idle" | "working"
    step: str | None = None
    batchId: str | None = None
    label: str = ""
    lastDone: bool = False


class BatchItem(BaseModel):
    id: str
    file: str
    channel: str
    rows: int = 0
    status: str  # "masuk" | "diproses" | "bersih" | "tinjau"
    trust: str = ""  # status kepercayaan asli dataset
    t: int = 0
    # Isi baris diambil terpisah lewat GET /stage/batches/{id}; kolom ini hanya penampung supaya tampilan lama tidak error.
    cols: list[str] = Field(default_factory=list)
    raw: list = Field(default_factory=list)
    clean: list = Field(default_factory=list)
    stats: dict = Field(default_factory=lambda: {"kept": 0, "dup": 0, "empty": 0, "fmt": 0})


class ApiInfo(BaseModel):
    configured: bool = False
    key_prefix: str | None = None  # awalan kunci saja (bukan kunci utuh)
    last_used: int | None = None  # epoch milidetik


class StageSummaryOut(BaseModel):
    flow: StageFlow
    trend: list[TrendDay]
    categories: list[NameValue]
    channels: list[NameValue]
    low_stock: list[StockItem] = []
    hermes: list[HermesItem] = []
    feed: list[FeedItem]
    events: list[EventItem] = Field(default_factory=list)
    agent: AgentState = Field(default_factory=AgentState)
    batches: list[BatchItem] = Field(default_factory=list)
    api: ApiInfo = Field(default_factory=ApiInfo)
    # False sampai log Hermes tersimpan di backend; Panggung menampilkan "Belum tersambung".
    hermes_connected: bool = False