# Talatee Personal Big Data Platform — Architecture & Phase 1 Spec

> Dokumen ini adalah SATU-SATUNYA sumber konteks yang dibutuhkan untuk membangun Phase 1.
> Baca dari atas ke bawah sebelum mulai coding. Update checklist di bagian bawah setiap
> selesai satu langkah, supaya sesi kerja berikutnya (bahkan kalau kamu lupa detailnya)
> tetap tahu persis progres sampai mana.

## Visi
"Saya punya satu tempat pribadi yang menjadi memori seluruh data saya. Apa pun sumbernya, data
masuk → tersimpan aman → otomatis tercatat → bisa ditemukan lagi kapan saja → dan di masa depan
bisa digunakan untuk apa pun."

Platform ini adalah **fondasi data**, bukan produk akhir. Talatee Automation Studio dan aplikasi
lain di masa depan akan menjadi *client* yang memakai platform ini lewat API — mereka bukan
bagian dari platform ini.

## Prinsip Inti (jangan dilanggar di kode apa pun)
1. Data apa pun bisa masuk melalui **connector** yang seragam interfacenya.
2. **Raw data tidak pernah di-overwrite.** Setiap ingestion = batch baru dengan file baru, walau
   sumber dan isinya sama persis dengan sebelumnya.
3. Setiap ingestion punya **metadata lengkap**: source, connector, waktu, batch, jumlah record,
   schema, status, lokasi penyimpanan.
4. API/dashboard selalu membaca dari **metadata DB (PostgreSQL)**, tidak pernah scan langsung ke
   raw storage untuk keperluan tampilan.
5. Raw data = source of truth. Cleaning/standardization/analysis akan jadi layer/versi terpisah
   di atasnya nanti — tidak pernah menimpa raw.
6. **Ingestion Engine tidak boleh tahu detail spesifik sumber data apa pun.** Ia hanya bicara ke
   `Connector` interface yang seragam. Connector baru = class baru yang implement interface,
   didaftarkan ke registry. Core engine (`app/ingestion/engine.py`) tidak boleh diubah untuk
   menambah connector baru.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI
- **ORM / migration**: SQLAlchemy 2.x + Alembic
- **Metadata DB**: PostgreSQL 16
- **Raw storage**: MinIO (S3-compatible object storage), diakses lewat `boto3` atau `minio` SDK
- **Orkestrasi lokal**: Docker Compose
- Jangan tambah komponen lain (Redis, Celery, message queue, dll) di Phase 1 kecuali benar-benar
  kepepet butuh — Phase 1 murni tentang pipeline ingest → simpan → catat → query.

## Arsitektur Alur Data

```
Connector (interface: connect(), fetch(), get_metadata())
    ↓
Ingestion Engine (orchestrator, connector-agnostic)
    1. Terima raw data dari connector
    2. Validasi minimal (bisa dibaca/di-parse, tidak korup/kosong)
    3. Generate batch_id (UUID) + hitung checksum (SHA-256) file
    4. Simpan raw file ke MinIO (path terstruktur, immutable)
    5. Simpan metadata batch + file ke PostgreSQL
    6. Update/registrasi entry di tabel `datasets` (buat baru kalau belum ada, atau update
       stats kalau sudah ada)
    ↓
API layer = query di atas metadata DB (fondasi untuk dashboard UI nanti)
```

## Skema Database (metadata) — PostgreSQL

```
sources
  id            UUID PK
  name          VARCHAR       -- misal "Shopee", "Manual Upload"
  type          VARCHAR       -- misal "marketplace", "file_upload", "pos", "api"
  status        VARCHAR       -- "active" | "inactive"
  created_at    TIMESTAMP

connectors
  id            UUID PK
  source_id     UUID FK -> sources.id
  name          VARCHAR       -- misal "Shopee Order API Connector"
  type          VARCHAR       -- identifier unik dipakai registry, misal "file_upload_csv"
  config        JSONB         -- config spesifik connector (kredensial disimpan terpisah/env, bukan di sini)
  status        VARCHAR
  created_at    TIMESTAMP

datasets
  id            UUID PK
  source_id     UUID FK -> sources.id
  name          VARCHAR       -- misal "Shopee Orders"
  description   TEXT
  schema        JSONB         -- schema hasil inferensi dari batch terakhir/gabungan
  created_at    TIMESTAMP
  updated_at    TIMESTAMP

batches
  id                  UUID PK
  dataset_id          UUID FK -> datasets.id
  connector_id        UUID FK -> connectors.id
  started_at          TIMESTAMP
  finished_at         TIMESTAMP NULLABLE
  status              VARCHAR   -- "running" | "success" | "partial_failed" | "failed"
  records_received    INTEGER
  records_saved        INTEGER
  records_failed       INTEGER
  error_message       TEXT NULLABLE

files
  id             UUID PK
  batch_id       UUID FK -> batches.id
  filename       VARCHAR
  storage_path   VARCHAR       -- path lengkap di MinIO
  file_size      BIGINT        -- bytes
  checksum       VARCHAR       -- SHA-256 hex
  uploaded_at    TIMESTAMP
```

Relasi: `sources 1--N connectors`, `sources 1--N datasets`, `datasets 1--N batches`,
`connectors 1--N batches`, `batches 1--N files`.

## Struktur Path Raw Storage (MinIO)
```
raw/{source_name_slug}/{yyyy}/{mm}/{dd}/{batch_id}_{original_filename}
```
Contoh: `raw/shopee/2026/08/17/8f3a2b1c-..._orders_20260817.csv`

Bucket name: `talatee-raw` (buat sekali saat startup kalau belum ada).

## Struktur Folder Project

```
talatee-data-platform/
├── docker-compose.yml
├── .env.example
├── ARCHITECTURE.md              <- file ini
├── requirements.txt
├── alembic.ini
├── app/
│   ├── main.py                  # FastAPI entrypoint, include semua router, health check
│   ├── config.py                # Settings via pydantic-settings, baca dari .env
│   ├── db/
│   │   ├── session.py           # SQLAlchemy engine + SessionLocal + get_db() dependency
│   │   └── base.py              # Declarative Base class
│   ├── models/                  # satu file per tabel, SQLAlchemy ORM models
│   │   ├── source.py
│   │   ├── connector.py
│   │   ├── dataset.py
│   │   ├── batch.py
│   │   └── file.py
│   ├── schemas/                 # Pydantic request/response schemas per resource
│   │   ├── source.py
│   │   ├── dataset.py
│   │   └── batch.py
│   ├── connectors/
│   │   ├── base.py              # abstract class Connector (connect/fetch/get_metadata)
│   │   ├── registry.py          # dict/mapping connector type -> class, dipakai engine
│   │   └── file_upload.py       # connector pertama: terima file upload langsung
│   ├── ingestion/
│   │   └── engine.py            # class IngestionEngine: orchestrator penuh
│   ├── storage/
│   │   └── minio_client.py      # wrapper: upload_file(), get_file(), ensure_bucket()
│   └── api/
│       └── routes/
│           ├── health.py
│           ├── ingestion.py     # POST /ingest/upload (trigger file_upload connector)
│           ├── sources.py       # GET /sources, GET /sources/{id}
│           ├── datasets.py      # GET /datasets, GET /datasets/{id}
│           └── batches.py       # GET /batches, GET /batches/{id}, GET /files/{id}/download
├── migrations/                  # Alembic migration files (auto-generated)
└── tests/
    └── test_ingestion_e2e.py    # test end-to-end: upload -> cek MinIO -> cek Postgres
```

## docker-compose.yml (isi lengkap)

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: talatee
      POSTGRES_PASSWORD: talatee
      POSTGRES_DB: talatee_platform
    ports:
      # Host port 5434 (bukan 5432 default) — hindari bentrok dengan Postgres native
      # yang mungkin sudah terinstall/jalan sebagai service di komputer lokal.
      - "5434:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: talatee
      MINIO_ROOT_PASSWORD: talatee123
    ports:
      - "9000:9000"   # API
      - "9001:9001"   # Console web UI, buat cek isi bucket manual
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
```

## .env.example

```
DATABASE_URL=postgresql://talatee:talatee@localhost:5434/talatee_platform
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=talatee
MINIO_SECRET_KEY=talatee123
MINIO_BUCKET=talatee-raw
MINIO_SECURE=false
```

---

# Phase 1 — Rencana Kerja Detail

Kerjakan **berurutan**. Jangan mulai langkah berikutnya sebelum checklist langkah sebelumnya
lolos beneran (dites nyata, bukan diasumsikan jalan). Setelah satu langkah lolos, centang
checklist-nya di bagian paling bawah file ini.

### Langkah 1 — Scaffold Project
Buat struktur folder di atas, `docker-compose.yml`, `.env.example`, `requirements.txt` dasar
(fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, python-dotenv atau pydantic-settings,
minio atau boto3, python-multipart untuk file upload).

Buat `app/main.py` minimal dengan satu endpoint `GET /health` yang return `{"status": "ok"}`.

Jalankan `docker compose up -d`, init alembic (`alembic init migrations`), arahkan
`alembic.ini` / `env.py` ke `DATABASE_URL` dari `.env`.

**Checklist selesai:**
- [x] `docker compose up -d` jalan tanpa error, `docker ps` menunjukkan postgres & minio healthy
      *(dites di lokal user, Windows)*
- [x] MinIO console bisa diakses di `localhost:9001` dan login pakai kredensial di atas
      *(dites di lokal user)*
- [x] `uvicorn app.main:app --reload` jalan, `GET /health` di `localhost:8000/health` return 200
      *(dites di sandbox Claude DAN di lokal user, browser: `{"status":"ok"}`)*
- [x] SQLAlchemy bisa konek ke Postgres (test simple `SELECT 1`)
      *(dites di lokal user setelah fix port bentrok — lihat catatan sesi kerja di bawah)*
- [x] `alembic init migrations` sudah jalan dan `alembic.ini` terhubung ke `DATABASE_URL`
      *(env.py baca `settings.database_url` dari `.env`, `target_metadata = Base.metadata`)*

### Langkah 2 — Data Model Inti
Buat SQLAlchemy models untuk 5 tabel (`sources`, `connectors`, `datasets`, `batches`, `files`)
persis sesuai skema di atas. Generate migration lewat
`alembic revision --autogenerate -m "init core tables"`, lalu `alembic upgrade head`.

**Checklist selesai:**
- [x] Semua 5 model dibuat sesuai skema, relasi FK benar
      *(dites: `alembic revision --autogenerate` deteksi persis 5 tabel, tanpa diff aneh)*
- [x] Migration ter-generate dan berhasil di-apply ke Postgres tanpa error
      *(revision `3f158c766bcf_init_core_tables.py`, `alembic upgrade head` sukses)*
- [x] Cek manual lewat `psql` atau tool DB client: kelima tabel ada dengan kolom yang benar
      *(dites: `\dt` menunjukkan 6 tabel termasuk `alembic_version`; `\d sources` sesuai skema)*
- [x] Bisa insert 1 row manual ke `sources` lewat Python shell/script sebagai sanity check
      *(dites: insert berhasil, id `fca3975e-8c71-4905-a8a3-671195ec66a4`)*

### Langkah 3 — Ingestion Engine Core
Buat `app/connectors/base.py`: abstract class `Connector` dengan method `connect()`, `fetch()`
(return raw bytes/file-like + info dasar), `get_metadata()` (return dict: source_name,
connector_type, dll).

Buat `app/ingestion/engine.py`: class `IngestionEngine` dengan method utama
`ingest(connector: Connector, dataset_name: str, ...)` yang menjalankan urutan:
validasi → generate batch_id & checksum → upload ke MinIO lewat `storage/minio_client.py` →
simpan record ke `batches` dan `files` → update/create `datasets`.

Buat `app/connectors/registry.py`: dict sederhana `{"file_upload_csv": FileUploadConnector, ...}`
supaya connector baru tinggal didaftarkan di sini, tanpa ubah `engine.py`.

**Checklist selesai:**
- [x] `Connector` abstract class dibuat dengan interface yang jelas
      *(`connect()`, `fetch()` -> `FetchResult`, `get_metadata()`)*
- [x] `IngestionEngine.ingest()` bisa dipanggil dari Python script langsung (belum lewat API)
      dan berhasil: file tersimpan di MinIO + row baru muncul di `batches` dan `files`
      *(dites via `test_langkah3.py`: TEST 1 sukses, upload ke MinIO asli, batch.status="success")*
- [x] Kalau proses gagal di tengah (misal file korup), status batch tercatat `failed` dengan
      `error_message` terisi, bukan crash tanpa jejak
      *(dites: TEST 3 — data kosong -> batch.status="failed", error_message terisi jelas)*

**Bonus validasi (di luar checklist asli, tapi penting dibuktikan):**
- Upload file IDENTIK dua kali -> 2 batch id berbeda (prinsip raw immutable, TEST 2) ✅
- Auto-create source/connector/dataset TIDAK duplikat walau di-ingest berkali-kali ✅
  *(dites di sandbox Claude dengan Postgres asli: 3x ingest -> tetap 1 source, 1 connector)*

### Langkah 4 — Connector Pertama: File Upload
Buat `app/connectors/file_upload.py`: implement `Connector` interface untuk menerima file
CSV/Excel yang di-upload langsung (bukan fetch dari luar). Ini connector paling sederhana
karena tidak butuh koneksi eksternal apa pun — cocok untuk membuktikan seluruh pipeline jalan.

**Checklist selesai:**
- [x] `FileUploadConnector` implement semua method interface
- [x] Terdaftar di `registry.py`
      *(`file_upload_csv` dan `file_upload_excel`, plus helper `EXTENSION_TO_CONNECTOR_TYPE`
      dan `get_connector_class()` untuk dipakai endpoint upload di Langkah 5)*
- [x] Bisa terima file CSV dan Excel (minimal .csv dan .xlsx)
      *(dites: parsing kolom + jumlah baris benar untuk keduanya, lewat unit test DAN
      integrasi penuh via IngestionEngine + Postgres asli + MinIO asli di lokal user)*

**Bonus validasi:** ekstensi tidak didukung ditolak jelas saat instantiate; CSV kosong dan Excel
korup keduanya tertangkap rapi jadi `batch.status="failed"` (bukan crash) lewat IngestionEngine;
`dataset.schema` ter-overwrite benar dari kolom hasil parsing batch terakhir.

### Langkah 5 — API Dasar
Buat endpoint-endpoint di `app/api/routes/`:
- `POST /ingest/upload` — terima file upload (multipart/form-data) + parameter `source_name`,
  `dataset_name`, trigger `IngestionEngine` dengan `FileUploadConnector`
- `GET /sources` — list semua sources
- `GET /sources/{id}` — detail satu source
- `GET /datasets` — list semua datasets (dengan info ringkas: total records, last updated)
- `GET /datasets/{id}` — detail dataset + riwayat batches-nya
- `GET /batches` — list batches (bisa difilter by dataset_id)
- `GET /batches/{id}` — detail satu batch + files-nya
- `GET /files/{id}/download` — download raw file asli dari MinIO

**Checklist selesai:**
- [x] Semua endpoint di atas jalan dan return response sesuai (test manual lewat
      `/docs` Swagger UI bawaan FastAPI)
- [x] Upload file lewat `/ingest/upload` benar-benar memicu seluruh pipeline dan datanya
      langsung bisa di-query lewat endpoint lain
      *(dites lengkap di lokal: upload CSV 20 baris -> POST /ingest/upload 201 sukses ->
      GET /datasets menunjukkan total_records=20 -> GET /datasets/{id} menunjukkan schema +
      riwayat batch -> GET /batches/{id} menunjukkan detail + file -> GET /files/{id}/download
      menghasilkan file yang isinya identik 100% dengan file asli yang diupload)*

### Langkah 6 — Verifikasi End-to-End
Tulis test di `tests/test_ingestion_e2e.py` yang:
1. Upload file CSV contoh lewat `/ingest/upload`
2. Assert response sukses dan berisi `batch_id`
3. Assert file benar-benar ada di MinIO di path yang sesuai struktur
4. Assert row `batches` dan `files` di Postgres sesuai (status success, checksum cocok)
5. Assert `GET /datasets/{id}` menunjukkan dataset baru dengan record count yang benar

**Checklist selesai:**
- [x] Test end-to-end di atas lolos semua
      *(dites di lokal: `pytest tests/test_ingestion_e2e.py -v` -> 2 passed, pakai Postgres &
      MinIO sungguhan — bukan mock)*
- [x] Upload file yang sama dua kali menghasilkan DUA batch terpisah (bukti prinsip
      "raw tidak pernah di-overwrite" benar-benar berjalan)
      *(dites otomatis via `test_upload_same_file_twice_creates_two_batches`: 2 batch_id
      berbeda, storage_path berbeda, checksum identik)*

---

# Eksplisit di Luar Scope Phase 1
- AI Agent, analytics, automation trigger (ini Phase 6 nanti — jangan dikerjakan dulu)
- Dashboard UI visual (Phase 1 cukup sampai API; UI menyusul di Phase 2+)
- Connector selain File Upload (Google Sheets, Shopee API, dll menyusul setelah Phase 1 lolos)
- Redis, Celery, message queue, scheduler

# Sumber Data yang Direncanakan (connector masa depan, bukan Phase 1)
Shopee, Lazada, TikTok Shop, POS/kasir, Excel, CSV, JSON, Google Sheets, REST API, database,
webhook — dan connector lain di masa depan.

---

# Progress Tracker
(Update bagian ini setiap selesai satu langkah — centang checklist di atas juga)

- [x] Langkah 1 — Scaffold Project (selesai & lolos semua checklist di lokal, 18 Agu 2026)
- [x] Langkah 2 — Data Model Inti (selesai & lolos semua checklist di lokal, 18 Agu 2026)
- [x] Langkah 3 — Ingestion Engine Core (selesai & lolos semua checklist di lokal, 18 Agu 2026)
- [x] Langkah 4 — Connector Pertama: File Upload (selesai & lolos semua checklist, 18 Agu 2026)
- [x] Langkah 5 — API Dasar (selesai & lolos semua checklist di lokal, 18 Agu 2026)
- [x] Langkah 6 — Verifikasi End-to-End (selesai & lolos semua checklist, 19 Agu 2026)

**PHASE 1 SELESAI SEPENUHNYA — semua 6 langkah lolos dengan verifikasi nyata di lokal
(bukan asumsi). Siap lanjut ke Phase 2 (Dashboard UI) kalau/ketika dibutuhkan.**

**Catatan sesi kerja terakhir:**

Keputusan desain berikut sudah **dikunci untuk Phase 1** (hasil review sebelum coding dimulai).
Jangan direvisi lagi kecuali ditemukan masalah nyata saat implementasi/testing:

1. **Source & Connector & Dataset → AUTO-CREATE.** `POST /ingest/upload` menerima `source_name`
   + `dataset_name`. Di dalam `IngestionEngine.ingest()`:
   - Cari `sources` by `name` → kalau belum ada, buat baru (`type="file_upload"`,
     `status="active"`).
   - Cari `connectors` by `source_id` + `type` (`file_upload_csv` / `file_upload_excel`,
     ditentukan dari ekstensi file) → kalau belum ada, buat baru.
   - Cari `datasets` by `source_id` + `name` → kalau belum ada, buat baru; kalau sudah ada,
     dipakai lagi (batch baru masuk ke dataset yang sama).
   - Tidak ada endpoint `POST /sources` / `POST /connectors` di Phase 1.

2. **`Connector.connect()` = no-op untuk `FileUploadConnector`.** Method ini tetap ada di
   interface (dibutuhkan connector lain yang butuh koneksi eksternal, misal API), tapi untuk
   file upload tidak melakukan apa-apa karena file sudah tersedia di memory/multipart saat
   `fetch()` dipanggil.

3. **Checksum SHA-256 = integrity check only, BUKAN dedup key.** Upload file identik dua kali
   tetap menghasilkan 2 batch terpisah (sesuai Prinsip Inti #2). Jangan ada logic yang menolak
   atau men-skip upload karena checksum sama dengan batch sebelumnya.

4. **`datasets.schema` = overwrite dari schema batch terakhir.** Bukan merge/gabungan antar
   batch. Kalau ada schema drift, versi lama tidak disimpan di tabel ini — merge/versioning
   schema jadi urusan layer cleaning/standardization di masa depan (Prinsip Inti #5), bukan
   Phase 1.

Langkah 1 SELESAI dan lolos semua checklist di lokal (Windows, 18 Agustus 2026).

**Isu yang ditemukan & solusinya (penting untuk diingat):** Port Postgres di `docker-compose.yml`
dan `DATABASE_URL` di `.env` **BUKAN 5432 default, tapi 5434** (`"5434:5432"` di docker-compose,
`localhost:5434` di `.env`). Ini karena di komputer development ada instalasi PostgreSQL native
Windows yang jalan sebagai proses terpisah dan kebetulan juga listen di port 5432 — bikin koneksi
dari SQLAlchemy/psycopg2 kadang nyasar ke Postgres native itu (bukan ke container Docker),
menghasilkan error `password authentication failed for user "talatee"` walau kredensial di
`docker-compose.yml` sudah benar. Solusinya: pindahkan port host container ke 5434 (bukan matikan
service Windows-nya, supaya tidak mengganggu proses lain di komputer yang sama). Port internal
container tetap 5432, cuma port host-nya yang beda. Kalau di masa depan pindah ke komputer lain
atau server, cek dulu apakah port 5432 default bebas dipakai atau perlu diganti lagi.

Progres teknis: struktur folder, `docker-compose.yml` (postgres port 5434→5432, minio 9000/9001),
`.env.example`, `requirements.txt`, `app/main.py` + `/health`, `app/config.py` (pydantic-settings),
`app/db/base.py`, `app/db/session.py`, `alembic init` + `env.py` (baca `DATABASE_URL` dari `.env`,
`target_metadata` sudah diarahkan ke `Base.metadata` supaya autogenerate di Langkah 2 langsung
jalan tanpa perlu edit `env.py` lagi) — semua sudah dibuat dan dites nyata: `/health` return 200,
`docker ps` healthy (postgres + minio), MinIO console bisa login, dan SQLAlchemy `SELECT 1`
berhasil return `1`.

**PHASE 1 SUDAH SELESAI SEPENUHNYA (19 Agustus 2026).** Semua 6 langkah lolos dengan bukti nyata
di lokal (bukan diasumsikan jalan). Kalau sesi kerja berikutnya melanjutkan project ini, mulai
dari Phase 2 (Dashboard UI, lihat bagian "Eksplisit di Luar Scope Phase 1") atau connector baru
di luar File Upload (Shopee, Google Sheets, dll — lihat bagian "Sumber Data yang Direncanakan").

Progres Langkah 6 (selesai, 19 Agustus 2026): `tests/test_ingestion_e2e.py` — 2 test otomatis
pakai `pytest` + `TestClient`, jalan terhadap Postgres & MinIO SUNGGUHAN (bukan mock):
`test_upload_end_to_end` (upload -> assert 201+batch_id -> assert file ada di MinIO dengan isi
identik -> assert row batches/files di Postgres sesuai termasuk checksum -> assert
GET /datasets/{id} record count benar) dan `test_upload_same_file_twice_creates_two_batches`
(bukti otomatis prinsip raw-immutable: 2 batch terpisah, storage_path beda, checksum sama).
`pytest` dan `httpx` ditambahkan ke `requirements.txt` sebagai dev-dependency.

Isu kecil saat setup (bukan bug kode): pytest awalnya gagal collect test dengan
`ModuleNotFoundError: No module named 'app'` karena folder `tests/` belum punya `__init__.py`
— pytest jadi cuma insert folder `tests/` ke `sys.path`, bukan root project. Fix: tambah file
kosong `tests/__init__.py`, supaya pytest mengenali `tests` sebagai package dan insert root
project (tempat folder `app/` berada) ke `sys.path` sebagai gantinya.

Ringkasan keseluruhan Phase 1 — struktur final project:
```
talatee-data-platform/
├── docker-compose.yml       # postgres (port 5434, lihat catatan port di atas) + minio
├── .env / .env.example
├── requirements.txt         # fastapi, sqlalchemy, alembic, minio, openpyxl, pytest, httpx, dll
├── alembic.ini
├── app/
│   ├── main.py               # entrypoint, include semua router
│   ├── config.py              # pydantic-settings
│   ├── db/{base,session}.py
│   ├── models/                # source, connector, dataset, batch, file
│   ├── schemas/                # source, batch, dataset (Pydantic response models)
│   ├── connectors/
│   │   ├── base.py            # interface Connector + FetchResult
│   │   ├── registry.py        # file_upload_csv/excel -> FileUploadConnector
│   │   └── file_upload.py     # connector pertama (CSV & Excel)
│   ├── ingestion/engine.py    # IngestionEngine — orchestrator penuh
│   ├── storage/minio_client.py
│   └── api/routes/            # health, ingestion, sources, datasets, batches
├── migrations/                 # alembic, 1 revision: init core tables
└── tests/test_ingestion_e2e.py
```

4 keputusan desain yang dikunci di awal (lihat riwayat di atas) semuanya terimplementasi dan
teruji: (1) auto-create source/connector/dataset, (2) `connect()` no-op untuk file upload,
(3) checksum untuk integrity check saja bukan dedup, (4) `dataset.schema` overwrite dari batch
terakhir.

---

# Phase 2 v1 — Dashboard UI (SELESAI, 23 Agustus 2026)

**Status: kode selesai DAN sudah tervalidasi visual penuh di browser lokal user — semua 5
halaman (Overview, Sources, Datasets, Jobs, Storage) dan navigasi antar-halaman dikonfirmasi
jalan dengan data asli.**

## Keputusan yang diambil (hasil elisitasi sebelum coding)
1. **Bentuk:** halaman web React terpisah (bukan server-rendered), sesuai mockup infografik awal.
2. **Scope v1:** semua sesuai infografik — Sources, Datasets, Jobs (=Batches), Files (nested di
   detail Job), Storage. Di luar scope: Schemas, Logs, Settings, Cleaning/Analysis/AI Agent
   (belum ada backend-nya, itu Phase 5/6).
3. **Lokasi:** folder terpisah di project yang sama, `talatee-data-platform/dashboard/`.

## Perubahan di backend (kecil, non-invasif)
- **Endpoint baru `GET /stats/overview`** (`app/api/routes/stats.py` + `app/schemas/stats.py`):
  agregasi total_records/total_datasets/total_sources/total_batches/total_storage_bytes,
  breakdown records per source, dan 10 batch terbaru. Dibutuhkan supaya halaman Overview tidak
  perlu N+1 request (tanpa endpoint ini, hitung total storage butuh fetch semua batch lalu semua
  file satu-satu). Tidak menyentuh `IngestionEngine` atau prinsip inti apa pun.
- **CORS diaktifkan** di `app/main.py` (`CORSMiddleware`), origin dibatasi ke
  `localhost:5173`/`127.0.0.1:5173` (default port Vite dev server) — supaya browser mengizinkan
  dashboard React (port beda) memanggil API.

## Stack frontend
React 19 + Vite + **Tailwind v4** (bukan v3 — v4 setup-nya beda, pakai plugin
`@tailwindcss/vite` + `@theme` di CSS, bukan `tailwind.config.js`/`postcss.config.js` terpisah)
+ `react-router-dom` (routing) + `recharts` (pie chart di Overview) + `lucide-react` (icon).

## Desain
Bukan tema navy-teal generik seperti infografik awal. Ditemukan metafora yang lebih pas dengan
prinsip inti platform (raw data tidak pernah ditimpa, cuma nambah terus) — visual "ledger/buku
besar": background gelap ink (`#0e1116`), aksen emas tua (`#c9a227`, bukan terracotta/teal
default), font monospace `IBM Plex Mono` untuk angka/ID batch/timestamp (kesan buku besar/log),
`IBM Plex Sans` untuk body text. Semua token warna & font ada di `dashboard/src/index.css` lewat
Tailwind `@theme` block.

## Struktur halaman yang dibuat
```
dashboard/src/
├── api/client.js        # satu tempat semua panggilan API (BASE_URL localhost:8000)
├── lib/
│   ├── format.js         # formatBytes, formatNumber, formatDateTime, formatRelative,
│   │                       statusStyle, colorForIndex (palet chart konsisten per-source)
│   └── useFetch.js       # hook fetch + loading/error state, dipakai semua halaman
├── components/
│   ├── Sidebar.jsx        # nav: Overview, Sources, Datasets, Jobs, Storage
│   ├── StatCard.jsx       # kartu angka besar (dipakai Overview)
│   ├── StatusBadge.jsx    # dot + label warna sesuai status batch
│   └── States.jsx         # LoadingState, ErrorState, EmptyState (konsisten di semua halaman)
├── pages/
│   ├── Overview.jsx        # stat cards + pie chart data-by-source + recent batches
│   ├── Sources.jsx         # tabel list source
│   ├── SourceDetail.jsx    # detail source + dataset terkait (difilter client-side dari
│   │                         GET /datasets, karena GET /sources/{id} tidak nested dataset)
│   ├── Datasets.jsx        # grid kartu dataset
│   ├── DatasetDetail.jsx   # schema (kolom hasil parsing) + riwayat batch nested
│   ├── Jobs.jsx             # tabel list semua batch
│   ├── JobDetail.jsx        # detail batch + daftar file + tombol download langsung
│   └── Storage.jsx          # total storage + bar breakdown per source + tabel dataset
└── App.jsx                # routing (react-router-dom), layout Sidebar + main content
```

## Validasi yang sudah dilakukan
- `npm run build` sukses tanpa error/warning (setelah fix urutan `@import` CSS)
- Backend `GET /stats/overview` dites dengan data nyata di Postgres sandbox — hasil agregasi
  benar (total_records, breakdown per source, recent_batches semua akurat)
- **Divalidasi visual di browser lokal user (23 Agustus 2026):** Overview (stat cards, donut
  chart "Data by Source" dengan legenda warna konsisten, list "Recently Added" dengan status
  badge hijau/merah) tampil sempurna dengan data asli (40 records, 6 datasets, 6 sources,
  storage 6.2 KB). Empat halaman lain (Sources, Datasets, Jobs, Storage) beserta navigasi
  detail (klik source/dataset/batch) juga dikonfirmasi jalan baik oleh user.
- Sempat ada insiden kecil saat setup: dashboard menunjukkan "Failed to fetch" karena user lupa
  menjalankan ulang `uvicorn` setelah menimpa file backend (`stats.py`, `main.py`) — bukan bug
  dashboard. Terlihat jelas dari Chrome DevTools Console: `ERR_CONNECTION_REFUSED` (bukan error
  CORS), artinya browser tidak menemukan server sama sekali di port 8000.

## Catatan untuk sesi kerja berikutnya
- Kalau backend restart/pindah port lagi (seperti insiden port 5432->5434 di Phase 1), ingat
  update `BASE_URL` di `dashboard/src/api/client.js` — saat ini hardcoded ke
  `http://localhost:8000` (port API, BUKAN port Postgres 5434).
- Bundle JS 573 KB (warning "chunk larger than 500kB") — belum masalah untuk v1 personal-scale,
  tapi kalau nanti mau dioptimasi, bisa code-split per halaman pakai `React.lazy()`.
- GET /sources/{id} tidak mengembalikan dataset nested — `SourceDetail.jsx` saat ini fetch
  SEMUA dataset lalu filter di client. Untuk skala besar (banyak dataset), sebaiknya nanti
  tambah query param `?source_id=` di `GET /datasets` (mirip yang sudah ada di
  `GET /batches?dataset_id=`) supaya tidak over-fetch.

---

# Fitur Tambahan Phase 2 — Halaman Upload (SELESAI, 23 Agustus 2026)

Dashboard tadinya read-only (semua halaman cuma GET). Ditambah halaman `/upload`
(`dashboard/src/pages/Upload.jsx`) supaya bisa trigger `POST /ingest/upload` langsung dari UI,
tidak perlu buka Swagger lagi untuk pemakaian sehari-hari.

## Yang dibuat
- `dashboard/src/pages/Upload.jsx` — form Source Name + Dataset Name + file (drag-drop atau
  klik), validasi ekstensi client-side (`.csv`/`.xlsx`) sebelum kirim ke server, tampilkan hasil
  (sukses ATAU gagal — batch gagal tetap ditampilkan rapi dengan `error_message`, konsisten
  dengan desain backend yang selalu return 201 + objek Batch apa pun hasilnya), tombol "Lihat
  Detail Job" dan "Upload Lagi".
- `api.uploadFile()` baru di `src/api/client.js` (multipart/form-data via `FormData`).
- Sidebar: tombol "Upload Data" dibedakan visual (solid aksen emas, bukan style nav item biasa)
  karena ini satu-satunya aksi tulis di dashboard yang sebelumnya semua read-only.
- Route `/upload` didaftarkan di `App.jsx`.

## Validasi
`npm run build` sukses. **Divalidasi visual penuh oleh user**: upload file asli lewat form →
hasil sukses dengan records_saved & batch ID → klik "Lihat Detail Job" → detail lengkap (files,
storage path, download) → cek di halaman Jobs, batch baru muncul di urutan teratas. User juga
sempat upload 2x tanpa sengaja — terkonfirmasi jadi 2 batch terpisah di list Jobs (bukti prinsip
raw-immutable tetap konsisten sampai ke fitur UI baru, bukan cuma di backend/API).

---

# Perubahan Palet Warna Dashboard (SELESAI, 23 Agustus 2026)

Tema visual diganti dari "ledger emas" (gold accent `#C9A227`) ke **hijau neon di atas hitam
pekat**, mengikuti identitas visual brand Talatee (referensi: infografik Talatee Automation
Group — background hitam, aksen hijau neon).

## Keputusan desain
Sebelum coding, didiskusikan dulu: infografik aslinya didesain untuk dilihat sekali (marketing),
sementara dashboard dipakai berulang tiap hari — jadi efek glow neon **tidak diterapkan ke semua
elemen**, hanya elemen interaktif utama (CTA, active nav state, hover), supaya tidak melelahkan
mata untuk pemakaian jangka panjang.

## Yang diubah
- `dashboard/src/index.css` — token warna: `--color-accent: #7cfc3c` (hijau neon), background
  `--color-ink: #0a0d0a` (hitam pekat), `--color-success` disamakan dengan accent (hijau = brand
  = "baik"). Ditambah 3 utility class glow: `.glow-accent` (kuat, untuk CTA utama),
  `.glow-accent-sm` (halus, untuk active state/hover), `.glow-text-accent` (belum dipakai, siap
  kalau perlu nanti).
- `dashboard/src/lib/format.js` — palet chart (`CHART_PALETTE`) diurutkan ulang, hijau brand jadi
  warna pertama/utama. Status `partial_failed` diubah dari `bg-accent` (kuning tua) supaya TIDAK
  sama dengan warna `success` yang sekarang juga hijau — dipisah pakai warna kuning terang
  (`#E8C547`) biar tetap jelas beda.
- `dashboard/src/components/Sidebar.jsx` — tombol "Upload Data" pakai `.glow-accent` (CTA paling
  penting), nav item aktif pakai `.glow-accent-sm` + border hijau tipis.
- `dashboard/src/pages/Upload.jsx` — tombol submit & "Upload Lagi" pakai `.glow-accent-sm`,
  drag-zone berubah jadi hijau + glow saat file di-drag di atasnya.

## Validasi
Build sukses, **dikonfirmasi visual oleh user langsung di browser** — semua halaman dicek
konsisten, efek glow di sidebar/tombol/drag-zone terlihat sesuai rencana, tidak ada bagian yang
kesulitan dibaca.

---

# Fitur Businesses (Multi-Klien) — SELESAI, 24 Agustus 2026

Perubahan struktural terbesar sejak Phase 1: platform ini awalnya diasumsikan "personal" (data
satu bisnis), ternyata dipakai untuk **mengelola data banyak klien berbeda** (Talatee sebagai
automation agency — kelola data resto, klinik, marketplace seller, dll sekaligus). Ditambah
layer `Business` di atas `Source` supaya data tidak lagi flat/campur semua source jadi satu.

## Keputusan produk (dikonfirmasi user sebelum coding)
1. Kategori business = **daftar tetap** (dropdown), bukan free text:
   `restoran`, `klinik`, `marketplace`, `retail`, `lainnya`.
2. Data lama (dari testing Phase 1/2) **tidak dihapus** — otomatis masuk ke business default
   "Belum Dikategorikan" (category="lainnya") lewat migration backfill.

## Perubahan skema database
```
businesses (BARU)
  id UUID PK, name VARCHAR, category VARCHAR, status VARCHAR, created_at TIMESTAMP

sources (DIUBAH)
  + business_id UUID FK -> businesses.id, NOT NULL
```
Relasi baru: `businesses 1--N sources` (di atas relasi lama `sources 1--N connectors/datasets`
yang tidak berubah).

Migration: `migrations/versions/ffd9f70c7dae_add_businesses_and_source_business_id.py`.
**Ditulis manual** (bukan autogenerate mentah) karena butuh backfill data 3 tahap supaya aman
diterapkan ke tabel `sources` yang SUDAH ADA ISINYA:
1. Tambah kolom `business_id` sebagai NULLABLE dulu
2. Insert 1 row business default "Belum Dikategorikan", lalu UPDATE semua source lama
   (business_id masih NULL) ke situ
3. Baru set `business_id` jadi NOT NULL + FK constraint

Divalidasi 2x: (1) simulasi penuh di sandbox Claude — revert model ke versi "sebelum", apply
migration awal, isi data uji meniru source lama, baru terapkan model+migration baru dan buktikan
backfill jalan aman; (2) **diterapkan ke database asli user** — `alembic upgrade head` sukses,
```

verifikasi manual (`psql`) menunjukkan seluruh 8 source lama user (`Manual Test`, `Toko
Kelontong`, dll) otomatis ter-backfill ke business "Belum Dikategorikan" tanpa kehilangan data.

## Perubahan Engine & API
- `IngestionEngine.ingest()` sekarang terima `business_name` + `business_category` (opsional,
  default "lainnya"). Auto-create business dengan pola sama seperti source/dataset — KALAU
  business sudah ada (match by name), `business_category` yang dikirim di request **diabaikan**,
  tidak menimpa category yang sudah tersimpan (konsisten dengan prinsip "auto-create tidak
  mengubah data yang sudah ada").
- Source sekarang di-scope per business (`business_id` + `name`), bukan global by name saja —
  dua business berbeda boleh punya source dengan nama sama (misal sama-sama "Shopee").
- `POST /ingest/upload` nambah 2 field wajib/opsional: `business_name` (wajib),
  `business_category` (opsional, default "lainnya", divalidasi harus salah satu dari daftar
  tetap — kalau tidak, return 400).
- Storage path MinIO berubah format: `raw/{business_slug}/{source_slug}/{yyyy}/{mm}/{dd}/...`
  (sebelumnya `raw/{source_slug}/...` tanpa business).
- Endpoint baru: `GET /businesses` (list + agregasi total_sources/datasets/records per business),
  `GET /businesses/categories` (daftar tetap, dipakai dropdown UI), `GET /businesses/{id}`,
  `GET /businesses/{id}/sources`.
- `GET /sources` nambah filter opsional `?business_id=`.

## Perubahan Dashboard
- Halaman baru: `Businesses.jsx` (list dikelompokkan per kategori, dengan icon berbeda tiap
  kategori), `BusinessDetail.jsx` (info business + daftar source miliknya).
- `Sidebar.jsx`: nav item baru "Businesses", posisi kedua setelah Overview (jadi struktur utama
  browsing data, bukan lagi flat Sources).
- `Upload.jsx`: form nambah field "Business Name" + dropdown "Category" (fetch dari
  `GET /businesses/categories`, bukan hardcode di frontend — biar tidak drift dari backend).
- `Sources.jsx`: tabel nambah kolom "Business" (link ke business induk).
- `SourceDetail.jsx`: breadcrumb ke business induk (`Businesses / {nama business} / Sources`).

## Validasi
Backend: 8 skenario tervalidasi menyeluruh di sandbox Claude (auto-create business, category
diabaikan saat business sudah ada, backfill data lama, filter by business_id, validasi kategori
tidak valid → 400). `tests/test_ingestion_e2e.py` diupdate parameternya dan tervalidasi logic-nya
benar (lewat mock MinIO di sandbox — MinIO asli hanya ada di lokal user).

**Divalidasi visual penuh oleh user di browser lokal** (24 Agustus 2026): halaman Businesses
menunjukkan grouping per kategori dengan benar (kartu "Belum Dikategorikan" di grup "Lainnya"
dengan 8 sources/80 records dari data lama, tanpa kehilangan apa pun). Upload dengan business
baru ("Resto padang", kategori "Restoran") berhasil — storage_path baru terbentuk benar
(`raw/resto_padang/pos_kasir_dan_manual/...`), dan business baru langsung muncul di grup kategori
yang benar di halaman Businesses.

## Catatan untuk sesi kerja berikutnya
- Belum ada UI untuk **edit** business (ubah nama/kategori setelah dibuat) — kalau salah pilih
  kategori saat upload pertama kali, saat ini belum ada cara ubah lewat UI (harus manual lewat
  psql). Bisa jadi fitur Phase 2 lanjutan kalau dibutuhkan.
- Belum ada cara pindahkan source dari satu business ke business lain lewat UI.
- `dashboard/src/lib/format.js` — kalau nambah kategori baru ke `BUSINESS_CATEGORIES` di backend
  (`app/models/business.py`), ingat juga update `CATEGORY_META` di
  `dashboard/src/pages/Businesses.jsx` (icon + label) — dua tempat ini tidak otomatis sinkron.

---

# Talatee Bridge — Integrasi Produk Vertikal Pertama (SELESAI kode, 24 Agustus 2026)

Konfirmasi visi produk dari user: **Talatee = command center**, tempat pantau SEMUA klien
dari satu layar. **Buku Kas Warung = produk vertikal pertama** (project TERPISAH, Next.js +
TypeScript + SQLite, dibangun sebelumnya di luar percakapan ini, sudah di "Level 3/8" dari
roadmap 8-level mereka sendiri). Ke depan kemungkinan ada produk vertikal lain (buku-kas-warung
sendiri sudah punya constraint `business_type IN ('warung', 'laundry', 'bengkel')` di skemanya).

## Keputusan arsitektur
Bridge SATU ARAH (buku-kas-warung -> Talatee), BUKAN merge codebase. Alasan: buku-kas-warung
sudah punya data lifecycle governance sendiri yang matang (correction/void/duplicate detection)
— tidak ada untungnya dirombak. Talatee cukup terima SALINAN raw file tiap kali buku-kas-warung
berhasil ingest, lewat endpoint yang SUDAH ADA (`POST /ingest/upload`) — tidak perlu endpoint
baru sama sekali di sisi Talatee untuk ini.

## Perubahan di Talatee (project ini)
- `app/models/business.py` — `BUSINESS_CATEGORIES` diperluas: tambah `warung`, `laundry`,
  `bengkel` (cocok persis dengan `business_type` yang sudah dirancang di buku-kas-warung, tidak
  ada mapping/translasi, dikirim apa adanya).
- `dashboard/src/pages/Businesses.jsx` — `CATEGORY_META` dapat icon baru untuk 3 kategori itu
  (ShoppingBasket/warung, Shirt/laundry, Wrench/bengkel), dan `categoryOrder` diupdate.
- Divalidasi: `GET /businesses/categories` mengembalikan 8 kategori termasuk yang baru; upload
  dengan `business_category=warung` berhasil 201.

## File baru untuk buku-kas-warung (project terpisah, TIDAK ada di repo Talatee ini)
Dikirim ke user sebagai paket terpisah (`talatee-bridge-package.zip`), untuk ditempatkan di
project buku-kas-warung mereka:
- `lib/talatee-bridge/sync.ts` — modul `syncToTalatee()`. Prinsip paling penting: TIDAK PERNAH
  boleh menggagalkan/memperlambat alur utama buku-kas-warung — kegagalan sync (Talatee down,
  network error, dll) ditangkap semua di dalam fungsi ini sendiri, tidak pernah di-throw ulang.
  Fire-and-forget dari sisi pemanggil.
- `app/api/transactions/upload/route.ts` — diupdate MINIMAL (2 perubahan saja): baca file
  sekali jadi `Buffer` (bukan `.text()`/`.arrayBuffer()` terpisah), lalu 1 baris panggilan
  `syncToTalatee(...).catch(() => {})` setelah ingest lokal sukses. Logic ingest/lifecycle/
  duplicate-detection yang sudah ada TIDAK disentuh sama sekali.
- `INTEGRATION.md` — panduan pasang, termasuk cara test "Talatee down tidak menggagalkan
  upload" (skenario paling kritis untuk prinsip fire-and-forget ini).

## Bug yang ketemu & diperbaiki saat validasi statis
`new Blob([fileBytes])` di `sync.ts` awalnya gagal TypeScript strict mode: tipe `Buffer`
Node.js dianggap berpotensi membungkus `SharedArrayBuffer`, tidak cocok dengan tipe `BlobPart`.
Fix: `new Blob([new Uint8Array(fileBytes)])` — dites `tsc --noEmit --strict` sampai bersih
tanpa error.

## Keterbatasan validasi awal (sudah terlampaui — lihat update di bawah)
Saat kode ini pertama ditulis, belum bisa divalidasi runtime penuh di sandbox Claude (project
Next.js + better-sqlite3 native bindings terlalu besar/kompleks untuk di-setup ulang di sandbox
demi satu integrasi kecil). Yang divalidasi saat itu: sintaks & tipe TypeScript file `sync.ts`
bersih (`tsc --strict`) dan review manual logic route.ts.

## UPDATE — Divalidasi end-to-end SUNGGUHAN oleh user (24 Agustus 2026)
Ternyata `npm run build` pertama kali menemukan bug nyata: tipe `Database` custom interface di
`sync.ts` tidak cocok secara struktural dengan tipe asli `better-sqlite3` (`Statement.get()`
signature mismatch, TS2322) — diperbaiki dengan import tipe `Database.Database` asli dari
`better-sqlite3` alih-alih interface buatan sendiri. Juga ditemukan (bukan dari kode ini) 4
folder template nyasar di root buku-kas-warung (`api_reports_daily/`, `api_reports_weekly/`,
`api_transactions_upload/`, `lib_talatee-core/` — sisa dari paket distribusi
`talatee-level1-package` yang ke-taruh salah lokasi) yang ikut ke-typecheck dan bikin build
gagal; dihapus user setelah dikonfirmasi isinya cuma duplikat template.

Setelah kedua fix itu, `npm run build` sukses total (`Compiled successfully` + `Finished
TypeScript`, semua 15 route asli terdeteksi normal). Ditest 2 skenario kritis, keduanya lolos:

1. **Talatee DOWN saat upload** (tidak sengaja — backend belum dinyalakan) — upload di
   buku-kas-warung tetap sukses (`POST /api/transactions/upload 200`, UI tampilkan "✅ 1
   transaksi berhasil diproses"), kegagalan sync cuma masuk log
   (`[talatee-sync] error tak terduga: ECONNREFUSED ::1:8000`) — TIDAK menggagalkan response
   ke user. Prinsip paling penting dari bridge ini terbukti jalan di kondisi nyata.
2. **Talatee UP, upload sukses** — business baru "madura" otomatis muncul di dashboard Talatee
   (`localhost:5173/businesses`), masuk grup kategori "Warung" dengan icon yang benar, 1
   source/1 dataset/1 record — persis sesuai `business_type` yang terdaftar di buku-kas-warung.

**Bridge ini sekarang berstatus PRODUCTION-READY untuk kebutuhan lokal**, bukan lagi
"belum tervalidasi runtime".

## Selanjutnya (belum dikerjakan, di luar scope sesi ini)
- Distribusi self-install: docker-compose gabungan (Talatee + buku-kas-warung + n8n + WAHA)
  supaya client bisa `docker compose up` sendiri tanpa copy-paste file manual.
- Mode managed/SaaS: satu Talatee pusat di-hosting user, tiap warung baru daftar = 1 Business
  baru otomatis (struktur multi-bisnis Talatee sudah mendukung ini dari awal).

---

# Auth (API Key) — SELESAI kode, 25 Agustus 2026

Bagian pertama dari rencana besar "Talatee sebagai data platform pusat untuk ratusan-ribuan
klien" (didiskusikan setelah user mengonfirmasi visi arsitektur medallion: raw -> core ->
analytics, multi-tenant). Prioritas #1 karena paling berisiko kalau ditunda: sebelumnya
`POST /ingest/upload` bisa dipanggil SIAPA SAJA tanpa autentikasi.

## Yang dibuat
- **Tabel baru `api_keys`**: `id, name, key_hash, key_prefix, status, created_at, last_used_at`.
  Key ASLI (plaintext) tidak pernah disimpan — cuma SHA-256 hash-nya (`key_hash`), sesuai
  standar (mirip Stripe/GitHub token). `key_prefix` (12 karakter awal) disimpan terpisah untuk
  identifikasi di UI/log tanpa expose full key.
- `app/security/api_key.py` — dependency FastAPI `require_api_key`, baca header
  `Authorization: Bearer <key>`, validasi hash-nya ada di DB & `status="active"`, update
  `last_used_at`. Raise 401 kalau header tidak ada/format salah/key tidak ada/key revoked.
- `scripts/create_api_key.py` — generate key baru, plaintext cuma ditampilkan SEKALI di
  terminal, format `tal_<random 32 byte url-safe>`.
- `POST /ingest/upload` sekarang wajib `Depends(require_api_key)`.
- Migration: `7a2c9e5f3b41_add_api_keys_table.py` (nyambung dari `ffd9f70c7dae`).

## Keputusan desain penting
- **API key TIDAK di-scope ke satu business tertentu** — satu key mewakili "integrasi/produk
  terdaftar" (misal "Buku Kas Warung"), bukan "boleh akses business X saja". Alasan: satu
  produk (buku-kas-warung) bisa melayani BANYAK warung berbeda, masing-masing jadi business
  terpisah lewat auto-create — key-nya tetap satu untuk semua business yang dia kirim.
- **Dashboard (GET endpoints) SENGAJA belum dikunci API key.** Itu dipanggil langsung dari
  browser React — kalau dikasih key sekarang, key-nya kelihatan di DevTools siapa saja yang
  buka dashboard. Itu masalah beda (auth LOGIN dashboard, bukan auth machine-to-machine),
  ditandai sebagai kerjaan terpisah untuk nanti, bukan diselesaikan asal-asalan sekarang.

## Validasi
6 skenario tervalidasi menyeluruh di sandbox Claude (Postgres asli): tanpa header -> 401,
header format salah (bukan "Bearer") -> 401, key salah -> 401, key valid -> 201 sukses,
`last_used_at` ter-update setelah dipakai, key yang di-revoke -> 401. `tests/test_ingestion_e2e.py`
diupdate: fixture `api_key_header` generate key baru per sesi test, ditambah 1 test baru
`test_upload_requires_api_key`. Ketiga test lolos (2 di antaranya lewat mock MinIO di sandbox,
sesuai keterbatasan yang sama seperti sebelumnya — MinIO asli cuma ada di lokal user).

## UPDATE — Divalidasi end-to-end SUNGGUHAN oleh user (26 Agustus 2026)
Setelah dipasang di lokal, ditemukan & diperbaiki 2 masalah nyata (bukan bug logic, murni
konfigurasi/kelalaian saat pemasangan manual):
1. User sempat lupa mengganti baris `TALATEE_API_URL` yang SUDAH ADA sebelumnya (cuma nambah
   2 baris baru `API_KEY`/`SYNC_ENABLED`, baris `API_URL` lama masih `localhost` bukan
   `127.0.0.1`) — bikin `ECONNREFUSED ::1:8000` muncul lagi walau fix IPv4 sudah dikasih.
2. File `sync.ts` yang ditimpa ternyata masih versi SEBELUM API key ditambahkan (tidak ada
   baris `Authorization` sama sekali) — bikin Talatee menolak 401 walau `TALATEE_API_KEY` sudah
   terisi benar di `.env.local`. Diselesaikan dengan mengirim file `sync.ts` versi final sebagai
   file tunggal siap-download (bukan cuma snippet), plus verifikasi `Select-String -Pattern
   "Authorization"` sebelum restart — supaya ketahuan dari awal kalau file belum ke-timpa,
   bukan baru ketahuan setelah test gagal lagi.

Setelah kedua fix itu, log buku-kas-warung menunjukkan:
```
[talatee-sync] OK -> business "Warung Ibu Sari", batch e83e7f25-3a7a-4848-bac3-d0e28f5a726a, 30 records
```
Dan di dashboard Talatee (`localhost:5173/businesses`), "Warung Ibu Sari" muncul otomatis di
grup kategori "Warung" dengan 30 records — dikonfirmasi juga navigasi detail (Business ->
Sources -> Datasets breadcrumb) semuanya konsisten dan benar.

**Bridge + Auth API key SEKARANG BENAR-BENAR PRODUCTION-READY untuk kebutuhan lokal** —
tervalidasi ujung ke ujung, bukan cuma di level kode/logic lagi.

## Update paket bridge (buku-kas-warung)
`lib/talatee-bridge/sync.ts` diupdate: kirim `Authorization: Bearer ${TALATEE_API_KEY}` di
setiap request sync. Kalau `TALATEE_API_KEY` belum diisi di `.env.local`, sync dilewati dengan
log error jelas (bukan crash) — konsisten dengan prinsip "gagal sync tidak boleh ganggu upload
utama". `INTEGRATION.md` diupdate dengan langkah generate key + PENTING: pakai `127.0.0.1`
bukan `localhost` di `TALATEE_API_URL` (root cause insiden `ECONNREFUSED ::1:8000` yang sempat
dialami user — Windows resolve `localhost` ke IPv6 duluan, uvicorn default cuma listen IPv4).

## Belum dikerjakan (bagian dari rencana besar, sesi/fase berikutnya)
- Row-Level Security (RLS) di Postgres — isolasi multi-tenant yang dijamin DATABASE, bukan cuma
  disiplin kode aplikasi.
- Native Postgres SCHEMA terpisah (`vault`, `raw`, `core`, `analytics`, `ops`) — sekarang semua
  tabel masih di schema `public`.
- Layer transformasi `raw -> core` (paling berat secara teknis: setiap sumber data punya bentuk
  beda-beda, perlu "mapper" ke skema `core` yang seragam).
- Layer `analytics` (agregasi terjadwal).
- Auth untuk dashboard (login user, beda dari API key machine-to-machine ini).

# Hermes AI Agent Integration — MCP, AI Analyst, Redesign Navbar & Overview (SELESAI kode, 28 September 2026)

## Konteks
Tujuan awal: supaya Hermes (agent AI eksternal, Nous Research, jalan lokal di laptop
lewat Hermes Desktop) bisa "membaca" data bisnis Talatee dan dijawab langsung dari
dalam dashboard, tanpa buka aplikasi Hermes terpisah.

## Keputusan arsitektur
- **MCP (Model Context Protocol)** dipakai sebagai jembatan Hermes -> database
  Talatee, BUKAN akses SQL bebas. Hermes tidak pernah tahu password database dan
  tidak bisa menjalankan query sembarangan — semua lewat 5 tools bertanda tangan
  tetap (lihat di bawah).
- Semua tools MCP **hanya membaca dataset dengan `trust_status == "TRUSTED"`**
  (konsisten dengan Data Trust Spec Rule 06 yang sudah ada) — dataset yang belum
  trusted dikecualikan diam-diam dari agregasi, dan tiap tool melaporkan berapa
  dataset yang dikecualikan supaya angka 0 tidak disalahartikan sebagai "tidak ada
  data".
- Paket `mcp` HARUS dipin `==1.30.0` — versi >=2.0 menghapus class `FastMCP` yang
  dipakai `app/mcp/server.py`.

## File baru
- `app/mcp/server.py` — MCP server (stdio transport), 5 tools:
  `list_businesses`, `get_business_summary`, `query_transactions`,
  `get_sales_summary`, `get_top_products`. Semua query lewat SQLAlchemy
  parameterized query terhadap `Business -> Source -> Dataset -> Batch ->
  CoreTransaction` yang sudah ada, tidak menambah tabel baru.
- `app/api/routes/chat.py` — endpoint `POST /api/chat`, proxy ke API server
  OpenAI-compatible Hermes (`http://127.0.0.1:8642/v1/chat/completions`, BUKAN
  port dashboard Hermes `9119`). Stateless — riwayat percakapan dikirim ulang
  tiap request oleh frontend, backend tidak menyimpan sesi. Error handling
  eksplisit: 503 (Hermes API server mati), 504 (timeout 300 detik), 502
  (Hermes balas format tak terduga) — supaya dashboard tidak pernah menampilkan
  "Failed to fetch" mentah.
- `dashboard/src/pages/AIAnalyst.jsx` — panel chat asli di dalam dashboard,
  riwayat persist di `localStorage` browser (bukan backend), tombol
  "Percakapan baru" buat reset.
- `dashboard/src/pages/Hermes.jsx` — iframe ke UI Hermes asli (127.0.0.1:9119)
  buat akses penuh (Sessions/Files/Logs/dll) kalau dibutuhkan, dengan fallback
  "buka di tab baru" karena iframe http di halaman https (Vercel) diblokir
  browser (mixed content).
- `dashboard/src/pages/DataExplorer.jsx` — gabungan Databases+Integrations
  (dua laporan audit lintas-klien) jadi satu halaman bertab.
- `dashboard/src/pages/Settings.jsx` — halaman Settings pertama kali beneran
  berisi (sebelumnya ComingSoon kosong), tab "Sampah" memakai ulang komponen
  `Trash.jsx` yang sudah ada.

## Setup MCP di sisi Hermes (config, bukan kode — dicatat biar tidak lupa)
Ditambahkan lewat GUI Hermes (menu MCP -> Add Server, transport `stdio`):
```
command: C:/Python312/python.exe
args: -m app.mcp.server
env:
  PYTHONPATH=<path repo ini>
  DATABASE_URL=<connection string Neon — BEDA dari default lokal di app/config.py>
  PYTHONDONTWRITEBYTECODE=1
```
`PYTHONDONTWRITEBYTECODE=1` penting: tanpa ini, `uvicorn --reload` mendeteksi file
`.pyc` yang ditulis Python di `app/mcp/__pycache__/` sebagai "perubahan kode" dan
restart sendiri di tengah request yang sedang jalan (gejala: "Failed to fetch" random
di AI Analyst, hilang setelah baris ini ditambahkan).

API server OpenAI-compatible Hermes diaktifkan lewat menu Channels -> API server ->
Configure (`API_SERVER_ENABLED=true`, `API_SERVER_AUTH_KEY=<bebas, harus sama persis
dengan HERMES_API_KEY di .env Talatee>`, port default `8642`).

## Redesign Navbar (15 -> 9 item)
Item yang cuma ComingSoon kosong (Monitoring/Automations/Analytics/Reports) dibuang
dari sidebar (route-nya tetap ada di App.jsx, cuma tidak ditaut) — prinsip: sidebar
tidak boleh merangkap jadi peta roadmap, cukup menu yang beneran jalan. Databases +
Integrations digabung jadi "Data Explorer" bertab. Sampah dipindah jadi tab di dalam
Settings. "Talatee Laboratorium" di-rename "Eksperimen" (tabrakan nama dengan kolom
"01 — Laboratorium" di papan Proyek — dua konsep beda, nama sama, sumber kebingungan
nyata). Hasil akhir rata 9 item tanpa section header (grouping sempat dicoba, malah
menambah tinggi scroll — dibatalkan).

## Redesign Overview
- Checklist 6 item ("Laboratorium Data Pribadi", dst) di header dibuang — itu daftar
  fitur ala marketing, bukan informasi yang berguna dilihat tiap hari.
- Papan "Proyek Saya" (ProjectsBoard compact) dibuang dari Overview — bukan tentang
  data klien, halaman Proyek sendiri tidak diubah/tetap ada.
- Diagram statis "Data Flow (Arsitektur)" dibuang — tidak menampilkan data hidup,
  cuma ilustrasi, ikut bikin halaman terasa berantakan.
- Widget "Insight Otomatis" baru: dihitung dari data yang SUDAH ke-load di Overview
  (batch Failed terbaru, source paling dominan omzetnya, client tanpa data sama
  sekali) — TIDAK memanggil Hermes/API baru. Dinaikkan ke posisi lebih atas &
  dilebarkan penuh, dengan tombol "Tanya lebih lanjut" yang membawa topik insight
  itu ke AI Analyst lewat draft di `localStorage` (`talatee_ai_analyst_draft`).

## Validasi
Setiap potongan diverifikasi jalan sungguhan, bukan cuma "kelihatan benar":
- `app/mcp/server.py` di-import langsung terhadap `app.models` asli (bukan mock),
  5 tools ter-register, dicek lewat `mcp.list_tools()`.
- `app/api/routes/chat.py` ditest lewat `FastAPI TestClient` melawan server tiruan
  (fake OpenAI-compatible endpoint) untuk 4 skenario: normal (200), API key kosong
  (500), server mati (503), timeout (504).
- End-to-end sungguhan lewat browser: `AI Analyst` -> `/api/chat` -> Hermes ->
  `get_business_summary`/`list_businesses` -> jawaban asli dari database Neon,
  termasuk kasus Hermes jujur bilang omzet Rp0 karena dataset belum trusted.
- `npm run build` + `npm run lint` dijalankan ulang setiap kali ada perubahan
  dashboard — 0 error di semua tahap.

## Belum dikerjakan / diketahui belum aman (lihat PROJECT_CONTEXT_TALATEE.md #7)
- **Celah keamanan**: `AI Analyst` dan halaman `Hermes` (iframe) memanggil profile
  Hermes yang SAMA — tidak ada pembatasan tool. Rencana perbaikan: profile Hermes
  kedua dengan `agent.disabled_toolsets` (matikan `terminal`/`file`/`browser`/
  `code_execution`), API server terpisah, khusus dipakai AI Analyst.
- System prompt/persona Hermes belum disesuaikan — masih menjawab seperti asisten
  umum ("saya bisa bantu nulis artikel, coding, dll"), belum sadar dirinya
  "otak" Talatee.
- Tools tambahan yang diusulkan tapi ditunda (dinilai prematur untuk skala
  sekarang — 3 business, 2 di antaranya data uji coba): `get_system_health()`,
  context-switching toolset per halaman, monitoring otonom/digest harian otomatis.
