"""
Orchestrator penuh pipeline ingest -> simpan -> catat (Prinsip Inti #1-#6).

IngestionEngine TIDAK PERNAH tahu detail spesifik sumber data apa pun — ia hanya
bicara ke interface `Connector`. Menambah connector baru tidak boleh mengubah file ini.

Keputusan desain Phase 1 yang dikunci (lihat ARCHITECTURE.md):
1. Source/Connector/Dataset di-AUTO-CREATE di sini kalau belum ada — tidak ada
   endpoint admin terpisah.
2. checksum SHA-256 murni untuk integrity check, BUKAN dedup key — upload file
   identik dua kali tetap menghasilkan 2 batch terpisah (Prinsip Inti #2).
3. datasets.schema di-overwrite dari schema batch terakhir, bukan di-merge.

Keputusan Phase 2 (Businesses): Business juga di-AUTO-CREATE dengan pola yang sama.
Kalau business sudah ada (dicocokkan by name), category yang dikirim di request
BARU diabaikan — tidak menimpa category yang sudah di-set sebelumnya. Source
sekarang di-scope per business (dua business berbeda boleh punya source dengan
nama sama, misal sama-sama punya source "Shopee").
"""
import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.connectors.base import Connector
from app.ingestion.channel_guard import check_channel_column
from app.models import Business, Source, Connector as ConnectorModel, Dataset, Batch, File
from app.storage import minio_client


class IngestionEngine:
    def __init__(self, db: Session):
        self.db = db

    def ingest(
        self,
        connector: Connector,
        business_name: str,
        dataset_name: str,
        business_category: str = "lainnya",
    ) -> Batch:
        """Jalankan pipeline penuh untuk satu connector + satu dataset target.

        Selalu mengembalikan objek Batch (status "success" atau "failed"),
        tidak pernah crash tanpa jejak — kegagalan di connect()/fetch()/upload
        tercatat di batch.error_message.
        """
        metadata = connector.get_metadata()
        source_name = metadata["source_name"]
        connector_type = metadata["connector_type"]

        business = self._get_or_create_business(business_name, business_category)
        source = self._get_or_create_source(business, source_name)
        connector_row = self._get_or_create_connector(source, connector_type)
        dataset = self._get_or_create_dataset(source, dataset_name)

        batch = Batch(
            dataset_id=dataset.id,
            connector_id=connector_row.id,
            status="running",
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)

        try:
            connector.connect()
            result = connector.fetch()

            if not result.raw_data:
                raise ValueError(
                    "Data yang diterima dari connector kosong — kemungkinan file "
                    "korup atau tidak bisa di-parse."
                )

            # Kalau file punya kolom channel/platform, semua barisnya harus
            # cocok dengan source_name tujuan -- lihat app/ingestion/
            # channel_guard.py. Dipanggil SEBELUM upload ke MinIO supaya
            # tidak ada file yang sempat tersimpan dulu baru ketahuan salah.
            check_channel_column(result.raw_data, result.filename, source_name)

            checksum = hashlib.sha256(result.raw_data).hexdigest()
            storage_path = self._build_storage_path(
                business.name, source_name, batch.id, result.filename
            )

            minio_client.upload_file(
                storage_path,
                result.raw_data,
                result.content_type or "application/octet-stream",
            )

            file_row = File(
                batch_id=batch.id,
                filename=result.filename,
                storage_path=storage_path,
                file_size=len(result.raw_data),
                checksum=checksum,
            )
            self.db.add(file_row)

            record_count = result.record_count or 0
            batch.status = "success"
            batch.records_received = record_count
            batch.records_saved = record_count
            batch.records_failed = 0
            batch.finished_at = datetime.now(timezone.utc)

            if result.schema is not None:
                # Overwrite dari batch terakhir — keputusan Phase 1, bukan merge.
                dataset.schema_ = result.schema
            dataset.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(batch)
            return batch

        except Exception as exc:
            self.db.rollback()
            batch.status = "failed"
            batch.error_message = str(exc)
            batch.finished_at = datetime.now(timezone.utc)
            self.db.add(batch)
            self.db.commit()
            self.db.refresh(batch)
            return batch

    def _get_or_create_business(self, name: str, category: str) -> Business:
        business = self.db.query(Business).filter(Business.name == name).first()
        if business is None:
            business = Business(name=name, category=category, status="active")
            self.db.add(business)
            self.db.commit()
            self.db.refresh(business)
        return business

    def _get_or_create_source(self, business: Business, name: str) -> Source:
        source = (
            self.db.query(Source)
            .filter(Source.business_id == business.id, Source.name == name)
            .first()
        )
        if source is None:
            source = Source(
                business_id=business.id, name=name, type="file_upload", status="active"
            )
            self.db.add(source)
            self.db.commit()
            self.db.refresh(source)
        return source

    def _get_or_create_connector(self, source: Source, connector_type: str) -> ConnectorModel:
        connector_row = (
            self.db.query(ConnectorModel)
            .filter(
                ConnectorModel.source_id == source.id,
                ConnectorModel.type == connector_type,
            )
            .first()
        )
        if connector_row is None:
            connector_row = ConnectorModel(
                source_id=source.id,
                name=f"{source.name} - {connector_type}",
                type=connector_type,
                status="active",
            )
            self.db.add(connector_row)
            self.db.commit()
            self.db.refresh(connector_row)
        return connector_row

    def _get_or_create_dataset(self, source: Source, dataset_name: str) -> Dataset:
        dataset = (
            self.db.query(Dataset)
            .filter(Dataset.source_id == source.id, Dataset.name == dataset_name)
            .first()
        )
        if dataset is None:
            dataset = Dataset(source_id=source.id, name=dataset_name)
            self.db.add(dataset)
            self.db.commit()
            self.db.refresh(dataset)
        return dataset

    @staticmethod
    def _build_storage_path(
        business_name: str, source_name: str, batch_id: uuid.UUID, filename: str
    ) -> str:
        biz_slug = business_name.strip().lower().replace(" ", "_")
        src_slug = source_name.strip().lower().replace(" ", "_")
        now = datetime.now(timezone.utc)
        return f"raw/{biz_slug}/{src_slug}/{now:%Y}/{now:%m}/{now:%d}/{batch_id}_{filename}"
