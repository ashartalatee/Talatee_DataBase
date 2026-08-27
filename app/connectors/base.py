"""
Interface seragam untuk semua sumber data (Prinsip Inti #1 & #6).
IngestionEngine hanya bicara ke interface ini — tidak pernah tahu detail
spesifik connector apa pun. Connector baru = class baru yang implement ini,
didaftarkan di registry.py. engine.py tidak boleh diubah untuk menambah connector.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FetchResult:
    """Hasil fetch() dari sebuah connector."""

    raw_data: bytes
    filename: str
    content_type: str | None = None
    # Jumlah record di dalam file, kalau connector bisa menghitungnya (misal jumlah
    # baris CSV). None/0 kalau tidak relevan atau tidak diketahui — engine tidak
    # memaksa connector untuk parsing isi file.
    record_count: int | None = None
    # Schema hasil inferensi (misal daftar kolom CSV), opsional. Kalau diisi,
    # engine akan overwrite `datasets.schema` dengan ini (keputusan Phase 1: schema
    # = overwrite dari batch terakhir, bukan merge).
    schema: dict | None = None


class Connector(ABC):
    """Semua connector (file upload, API eksternal, scraper, dll) implement ini."""

    @abstractmethod
    def connect(self) -> None:
        """Siapkan koneksi ke sumber data. No-op untuk connector yang tidak butuh
        koneksi eksternal (misal file upload — datanya sudah ada di memory)."""
        raise NotImplementedError

    @abstractmethod
    def fetch(self) -> FetchResult:
        """Ambil raw data dari sumber. Dipanggil setelah connect(). Boleh raise
        exception kalau gagal/data korup — IngestionEngine yang menangani dan
        mencatatnya sebagai batch berstatus 'failed'."""
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self) -> dict:
        """Return dict minimal berisi:
        - source_name: str  (misal "Shopee", "Manual Upload")
        - connector_type: str  (identifier unik dipakai registry, misal "file_upload_csv")
        Dipakai IngestionEngine untuk resolve/auto-create Source & Connector row
        (keputusan Phase 1: auto-create, tidak ada endpoint admin terpisah)."""
        raise NotImplementedError
