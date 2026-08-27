"""
Registry connector type -> class. Connector baru cukup didaftarkan di sini —
tidak pernah perlu mengubah app/ingestion/engine.py (Prinsip Inti #6).
"""
from app.connectors.base import Connector
from app.connectors.file_upload import FileUploadConnector

CONNECTOR_REGISTRY: dict[str, type[Connector]] = {
    "file_upload_csv": FileUploadConnector,
    "file_upload_excel": FileUploadConnector,
}

# Ekstensi file -> connector type key. Dipakai endpoint upload (Langkah 5) untuk
# menentukan connector_type dari nama file, tanpa engine perlu tahu detail ini.
EXTENSION_TO_CONNECTOR_TYPE: dict[str, str] = {
    ".csv": "file_upload_csv",
    ".xlsx": "file_upload_excel",
}


def get_connector_class(connector_type: str) -> type[Connector]:
    if connector_type not in CONNECTOR_REGISTRY:
        raise ValueError(f"Connector type '{connector_type}' tidak terdaftar di registry.")
    return CONNECTOR_REGISTRY[connector_type]

