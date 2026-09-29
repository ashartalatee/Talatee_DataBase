# Talatee — Konteks Proyek

> Dokumen ini dibuat supaya siapa pun (termasuk AI assistant lain, atau Anda sendiri
> di laptop yang berbeda) bisa memahami proyek ini dengan cepat: apa tujuannya, apa
> yang sudah jalan, apa yang belum, dan keputusan-keputusan penting yang sudah diambil
> beserta alasannya. Terakhir diperbarui: 3 September 2026.
>
> Lihat juga: `PROJECT_CONTEXT.md` di project **Buku Kas Warung** — itu produk
> turunan/satelit dari Talatee, dokumennya saling melengkapi (bagian 8 di dokumen
> Buku Kas Warung menjelaskan hubungannya).

## 1. Apa ini

**Talatee** adalah *command center* — dashboard terpusat yang memantau banyak bisnis
kecil (warung, laundry, bengkel, restoran, dll) sekaligus dari 1 layar. Filosofinya:
"Data → Informasi → Peringatan → Keputusan → Pertumbuhan" — setiap business yang
terhubung (lewat produk satelit seperti Buku Kas Warung) otomatis mengirim data
mentahnya ke sini, lalu Talatee memvalidasi, menganalisis, dan menyajikannya sebagai
insight yang bisa langsung dipakai untuk keputusan.

**Peran Anda:** pemilik & operator tunggal. Talatee bukan produk yang dijual
langsung ke client — ini "laboratorium pribadi" Anda untuk eksperimen, menyiapkan
proyek baru, dan memonitor semua client yang sudah pakai produk turunannya (seperti
Buku Kas Warung).

## 2. Arsitektur teknis

```
Produk satelit (Buku Kas Warung, dll)
    │  POST /ingest/upload  (raw file, fire-and-forget dari sisi pengirim)
    ▼
FastAPI backend (Python)              ◄── jalankan: uvicorn app.main:app --reload
    │
    ├── app/config.py            (baca .env lewat pydantic_settings)
    ├── app/api/routes/*.py       (endpoint: businesses, sources, datasets,
    │                              batches, projects, lab_entries, auth, stats, dll)
    ├── app/security/*.py         (dashboard_session — login admin dashboard)
    ├── app/ingestion/*.py        (core_processor — proses data masuk)
    ├── app/models/*.py           (SQLAlchemy ORM)
    └── migrations/versions/*.py  (Alembic — migrasi skema database)
    │
    ├──────────────► PostgreSQL 16 (Docker, port 5434, db: talatee_platform)
    └──────────────► MinIO (Docker, port 9000 API / 9001 console, bucket: talatee-raw)

dashboard/ (React + Vite, port 5173)   ◄── jalankan: cd dashboard && npm run dev
    │  fetch ke localhost:8000
    ├── Overview               (ringkasan: total client, dataset, source, records)
    ├── Talatee Laboratorium   (daftar eksperimen)
    │   └── LabEntryDetail     (pipeline 7 langkah per eksperimen)
    ├── Proyek                 (kanban: 01 Laboratorium → 02 Siap Publikasi → 03 Live/Client)
    ├── Clients, Monitoring, Databases, Automations, Analytics, AI Analyst,
    │   Logs & Errors, Integrations  (menu ada di sidebar, sebagian besar
    │   belum diverifikasi datanya real atau placeholder — cek satu-satu
    │   kalau mau kembangkan)
    └── Login                  (autentikasi dashboard: bcrypt hash + session)
```

**Stack:** FastAPI (Python 3.12, di `venv/`), SQLAlchemy + Alembic, PostgreSQL 16
(Docker), MinIO (Docker, S3-compatible object storage untuk raw file), React + Vite
(dashboard).

**Cara jalankan dari nol:**
```powershell
# Backend
.\venv\Scripts\Activate.ps1
docker-compose up -d          # nyalakan Postgres + MinIO
uvicorn app.main:app --reload # jalan di localhost:8000

# Dashboard (terminal terpisah)
cd dashboard
npm run dev                   # jalan di localhost:5173
```

## 3. Fitur: status sebenarnya

### Sudah jalan
- Overview dashboard — metrik real dari database (client, dataset, source, records,
  storage)
- Ingestion pipeline — terima raw file dari produk satelit, simpan ke MinIO +
  metadata ke Postgres
- Proyek board (kanban 3 kolom) — tapi API-nya (`app/models/project.py`,
  `app/schemas/project.py`) sempat dimodifikasi bareng sesi ini, cek ulang kalau ada
  bug setelah migrasi kredensial
- Login dashboard admin (`auth.py`, `dashboard_session.py`, `Login.jsx`) — bcrypt
  password hash + session secret, dibuat dengan
  `scripts/generate_dashboard_credentials.py`. **Catatan jujur:** fitur ini ada di
  codebase tapi belum pernah didemonstrasikan/dites end-to-end dalam sesi kerja yang
  terekam di riwayat ini — kalau mau pakai, test dulu alurnya dari awal (buka
  `/login`, masukkan kredensial, pastikan redirect & session-nya benar).
- **Laboratorium pipeline UI** (`Laboratorium.jsx`, `LabEntryDetail.jsx`) — desain
  visual sudah dibangun ulang (badge nomor + ikon berwarna per step, tombol
  JALANKAN, panah penghubung), terhubung ke data asli untuk:
  - Step 1 Ambil Data ✅ (baca metadata dataset)
  - Step 2 Bersihkan Data ✅ (`POST /datasets/{id}/process`)
  - Step 3 Validasi ✅ (`GET /datasets/{id}/quality`)
  - Step 4 Analisis ✅ (`GET /datasets/{id}/insights`)
  - Step 6 Dashboard ✅ (reuse insights, render chart)
  - Step 5 Insight AI ❌ belum ada backend, UI-nya cuma "Segera hadir"
  - Step 7 Kirim ke WA ❌ belum ada integrasi WA di Talatee sama sekali

### Belum diverifikasi / kemungkinan besar belum ada
Menu sidebar berikut **ada tombolnya** tapi belum pernah dicek/dikembangkan dalam
riwayat kerja ini — jangan asumsikan sudah berfungsi tanpa dicek dulu: Clients,
Monitoring, Databases, Automations, Analytics, AI Analyst, Logs & Errors,
Integrations.

## 4. Insiden keamanan yang baru terjadi (3 September 2026) — PENTING DIBACA

Repo GitHub project ini **publik**. Ditemukan bahwa `.env.example` berisi
**kredensial asli** (bukan contoh generik) yang sudah lama ter-commit:
- `MINIO_ACCESS_KEY=talatee` / `MINIO_SECRET_KEY=talatee123`
- Password Postgres `talatee`/`talatee` (lewat `DATABASE_URL` di `.env.example`)

**Sudah ditangani** — kedua kredensial sudah diganti (di database-nya langsung via
`ALTER USER`/container recreate, BUKAN cuma di file konfigurasi) dan
`docker-compose.yml` sudah diubah supaya baca dari `${MINIO_ACCESS_KEY}` dkk, bukan
hardcode. `.env.example` sekarang isinya placeholder generik.

**Yang PENTING diketahui ke depan:**
- Password lama yang bocor (`talatee`/`talatee123`) **tetap ada di git history**
  repo ini selamanya (mengganti file tidak menghapus history). Ini bukan masalah
  besar SELAMA password-nya sudah tidak dipakai lagi — tapi jangan pernah pakai
  `talatee`/`talatee123` lagi untuk apa pun di project ini.
- **Ada 1 kredensial terkait yang MASIH belum diganti**: WAHA API key (`talatee123`)
  di project **Buku Kas Warung** (dicatat di `Setup_waha_n8n.md` project itu, tidak
  di-commit tapi tetap perlu diganti manual). Lihat `PROJECT_CONTEXT.md` Buku Kas
  Warung bagian 7.
- **Pelajaran untuk ke depan**: kalau bikin `.env.example` baru, SELALU isi dengan
  placeholder generik (`ganti-dengan-xxx-anda`), jangan pernah nilai asli walau
  "sementara" — kebiasaan ini yang menyebabkan insiden ini terjadi.

## 5. Environment variables

File `.env` (tidak di-commit) dan `.env.example` (di-commit, placeholder saja):

| Variabel | Untuk apa |
|---|---|
| `DATABASE_URL` | `postgresql://talatee:PASSWORD@localhost:5434/talatee_platform` |
| `MINIO_ENDPOINT` | `localhost:9000` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Kredensial MinIO (jangan pernah default lagi) |
| `MINIO_BUCKET` | `talatee-raw` |
| `MINIO_SECURE` | `false` untuk lokal (HTTP, bukan HTTPS) |
| `DASHBOARD_ADMIN_USERNAME` | Username login dashboard |
| `DASHBOARD_ADMIN_PASSWORD_HASH` | Hash bcrypt, generate lewat `scripts/generate_dashboard_credentials.py` |
| `SESSION_SECRET_KEY` | Random hex, generate dari script yang sama |
| `POSTGRES_PASSWORD` | Dipakai `docker-compose.yml` untuk inisialisasi container Postgres — **hati-hati**: env var ini CUMA berlaku saat volume Postgres pertama kali dibuat kosong. Kalau volume sudah ada isinya, ganti password harus lewat `ALTER USER` langsung ke database, bukan cuma ubah env var lalu restart container. |

`app/config.py` pakai `extra="ignore"` — variabel tambahan di `.env` yang tidak
dikenali skema `Settings` tidak akan bikin aplikasi crash (ini baru ditambahkan hari
ini, sebelumnya aplikasi crash kalau ada variabel asing seperti `POSTGRES_PASSWORD`
di `.env`).

## 6. Hubungan dengan produk satelit (Buku Kas Warung, dst)

- Setiap produk satelit **satu arah** mengirim raw file ke
  `POST /ingest/upload` — Talatee tidak pernah menulis balik ke database satelit.
- `business_category` di Talatee (`warung`, `laundry`, `bengkel`, dst) dipetakan
  1:1 dengan `business_type` di sisi satelit — istilahnya sengaja disamakan, tidak
  perlu mapping/translasi.
- Kalau sync gagal (satelit down, dsb), itu **tidak boleh** menggagalkan operasi
  Talatee — begitu juga sebaliknya, sync yang gagal di sisi satelit tidak boleh
  menggagalkan alur utama satelit itu sendiri (lihat prinsip fire-and-forget di
  `PROJECT_CONTEXT.md` Buku Kas Warung bagian 6).

## 6b. Data Trust — trust_status (ditambahkan 4 September 2026)

Mengikuti `TALATEE_DATA_TRUST_SPECIFICATION.md` (versi 1.0), `Dataset` sekarang
punya kolom `trust_status`: `INGESTED → VALIDATING → NEEDS_REVIEW → TRUSTED`.
Ini versi MINIMAL dari lifecycle 10-state di spec section 7 — sengaja belum
implementasikan `CORRECTING`/`REVALIDATING`/`RECONCILING` karena correction
model & reconciliation belum dibangun (lihat bagian 7 di bawah, masih issue
terbuka).

Aturan penting (spec section 12 — Trust Status ≠ Data Quality Score):
- **TRUSTED tidak pernah otomatis.** Harus lewat `POST /datasets/{id}/promote`,
  yang menolak (400) kalau `_compute_quality()` masih menghasilkan error.
- `GET /datasets/{id}/quality` (step "Validasi") sekarang punya efek samping:
  update `trust_status` jadi `NEEDS_REVIEW` (kalau ada error) atau `VALIDATING`
  (kalau lolos tapi belum di-promote).
- `POST /datasets/{id}/process` (step "Bersihkan Data") reset `trust_status`
  balik ke `INGESTED` setiap kali dijalankan ulang — karena `core_transactions`
  di-generate ulang dari raw file, trust lama tidak otomatis berlaku lagi.
- `GET /datasets/{id}/insights` (step "Analisis") sekarang **diblokir**
  (`{"blocked": true, ...}`, `processed: false`) kalau `trust_status != TRUSTED`
  — menutup Rule 06 spec ("Analytics must come from Trusted data").

**Batasan yang jujur perlu diketahui (status Sept 2026):** `TRUSTED` berarti
lolos completeness, duplicate check, DAN business rule `qty × harga_satuan =
subtotal` (lihat 6d di bawah — ditambahkan setelahnya). Jangan klaim di UI
bahwa data "100% benar" hanya karena statusnya TRUSTED — ikuti bahasa spec
section 36.

Migration: `b3f2a1c9d8e7_add_trust_status_to_datasets.py`.

## 6c. Dedup lintas-batch di core_processor.py (ditambahkan 4 September 2026)

Ditemukan lewat pemakaian nyata: dataset `d9036bae-...` (skincare marketplace)
punya 2 file (`bulan_1.csv`, `bulan_3.csv`) yang ke-upload 2x tidak sengaja —
59 `order_id` (118 baris) duplikat, TAPI Step 2 lama bilang "0 Duplikat"
karena cek duplikatnya cuma DALAM 1 batch (`seen_order_ids` direset tiap
batch), bukan lintas dataset. Risikonya nyata: kalau tidak ketahuan, revenue
Analytics untuk bulan itu akan double-counted.

Investigasi pakai `scripts/investigate_duplicate_order_ids.py <dataset_id>` —
skrip sekali-pakai untuk lihat order_id duplikat dari batch/file mana saja.

Perbaikan di `app/ingestion/core_processor.py`:
- `process_dataset()` sekarang 2-pass: Pass 1 baca & urai SEMUA batch dulu
  (urut `started_at`), Pass 2 baru tulis ke `core_transactions`.
- Kebijakan pemenang kalau `order_id` sama muncul >1 kali (baik dalam 1 file
  atau lintas file): **okurensi TERAKHIR menang** (asumsi: upload ulang =
  mau perbaiki data lama). Baris yang kalah TIDAK ditulis, tapi selalu
  dicatat di `summary["duplicates_skipped"]` (sesuai spec section 9.4 —
  jangan hapus duplikat tanpa dicatat).
- `_process_batch` diganti jadi `_parse_batch` (baca & urai saja, tanpa tulis
  DB) — logika parsing kolom/tipe data TIDAK berubah, cuma dipisah dari
  langkah tulis.
- Test baru: `tests/test_core_processor_dedup.py` (dedup lintas-batch +
  dedup dalam 1 batch yang sama).

**Batasan yang jujur:** kebijakan "terakhir menang" ini asumsi, bukan fakta
terverifikasi — kalau order_id kebetulan dipakai ulang untuk transaksi lain
(bukan revisi), bisa salah pilih baris. Belum ada correction model (section
14 spec) untuk menandai kasus itu secara eksplisit — assessment manual masih
perlu pakai skrip investigasi di atas kalau curiga.

## 6d. Business rule validation: qty x harga_satuan = subtotal (4 September 2026)

Sesuai rekomendasi setelah gap #2 dari daftar section 7 lama. Ditambahkan ke
`_compute_quality()` di `app/api/routes/core.py`:
- Untuk tiap baris dengan `qty`, `unit_price`, `subtotal` semuanya terisi,
  cek `qty * unit_price == subtotal` (pakai `Decimal`, bukan float, biar
  presisi).
- Mismatch masuk `errors` (BLOCK/CRITICAL sesuai spec section 9.7/10), bukan
  `warnings` — dataset dengan subtotal salah tidak akan bisa di-promote ke
  TRUSTED.
- `quality_score` sekarang juga dipotong oleh `business_rule_rate`, bukan
  cuma completeness & duplicate rate.
- Response `/quality` sekarang punya field baru: `subtotal_mismatch` (jumlah
  baris) dan `subtotal_mismatch_examples` (maks 5 contoh baris beserta nilai
  yang seharusnya) — ditampilkan di dashboard Step 3 (Validasi).
- Test: `tests/test_business_rules.py`.

**Batasan yang jujur:** baru cek 1 business rule (subtotal). Rule lain yang
mungkin relevan (konsistensi harga per produk, validasi enum status/kategori,
dst) belum dibangun — sengaja ditunda sampai ada kebutuhan nyata (prinsip
"Do Not Overengineer").

## 6e. Correction Model (spec section 14) — 5 September 2026

Tabel baru `corrections` (migration `d4e8f1a2b3c9`), model `app/models/correction.py`.
Endpoint: `POST/GET /datasets/{id}/corrections` (`app/api/routes/data_trust.py`).

- Dikunci ke `(dataset_id, order_id, field_name)`, BUKAN `core_transaction_id`
  — karena `core_transactions` di-generate ulang tiap "Bersihkan Data"
  dijalankan (baris lama dihapus, ID baru dibuat). Kalau correction dikunci
  ke ID lama, correction akan HILANG begitu diproses ulang.
- Append-only: correction baru untuk field yang sama = baris baru dengan
  `correction_version` lebih tinggi, bukan UPDATE. Versi tertinggi yang
  "aktif"/diterapkan.
- Correction TIDAK langsung mengubah `core_transactions` saat diajukan —
  baru berlaku setelah `POST /datasets/{id}/process` dijalankan lagi
  (`_load_active_corrections` & `_cast_correction_value` di
  `core_processor.py` yang menerapkannya, di Pass 2, sebelum baris ditulis).
- Field yang boleh dikoreksi dibatasi lewat `CORRECTABLE_FIELDS` (bukan
  `order_id`/`dataset_id`/`batch_id` — itu identitas baris, bukan nilai
  transaksi).
- **Batasan jujur:** baris tanpa `order_id` tidak bisa ditarget correction
  (tidak ada identitas stabil lintas reprocess).
- Frontend: tombol "Perbaiki" muncul di tiap contoh subtotal mismatch
  (Step 3), buka form inline (nilai benar + alasan) → `POST /corrections`.
- Test: `tests/test_correction_model.py` (3 test: apply-after-reprocess,
  versioning, reject non-correctable field).

## 6f. Reconciliation (spec section 16) — 5 September 2026

Tabel baru `reconciliations` (migration sama dengan 6e), model
`app/models/reconciliation.py`. Endpoint: `POST/GET /datasets/{id}/reconciliation`.

- Banding `source_total` (angka dari LUAR Talatee, diinput manual — mis. dari
  dashboard marketplace asli) vs `talatee_total` (`SUM(subtotal)` dari
  `core_transactions` yang `is_revenue=True`, difilter ke 1 bulan lewat
  `period_label` format `YYYY-MM`).
- `status = PASSED` kalau `abs(difference) <= tolerance` (default toleransi
  Rp1, bisa diubah per-request) — status `FAILED` disertai `hint` yang
  menjelaskan kemungkinan penyebab (spec section 16: refund, duplikat,
  filtering, dst).
- Append-only (snapshot historis) — tidak pernah update, supaya riwayat
  "apa yang pernah dicek, kapan, hasilnya apa" tetap ada (Rule 05).
- **Tidak** memengaruhi `trust_status` secara otomatis — ini pengecekan
  terpisah & opsional (tidak semua dataset akan punya angka pembanding dari
  luar).
- Frontend: kartu "Reconciliation" di bawah pipeline steps — input periode +
  total sumber, tampilkan hasil & riwayat.
- Test: `tests/test_reconciliation.py` (4 test: match, mismatch+hint,
  exclude non-revenue status, riwayat urut terbaru).

## 6g. Data Passport (spec section 6) — 5 September 2026

Endpoint `GET /datasets/{id}/passport` — MERANGKUM data yang sudah ada di
tabel lain (bukan tabel baru terpisah yang bisa tidak-sinkron): identitas +
trust_status dataset, provenance (jumlah batch, file asli + checksum-nya),
status kualitas terkini (`_compute_quality()` yang sama dipakai di Step 3),
jumlah correction sepanjang waktu, dan hasil reconciliation TERAKHIR (kalau
ada). Ini jawaban langsung untuk pertanyaan wajib di spec section 1: "data
ini dari mana, sudah diperiksa belum, apa yang berubah, kenapa dianggap
valid".

Frontend: kartu "Data Passport" di bawah pipeline steps, expand on-demand
(tidak auto-load supaya tidak nambah request kalau tidak dibutuhkan).

Test: `tests/test_data_passport.py` (3 test: struktur lengkap, refleksikan
jumlah correction, 404 untuk dataset yang tidak ada).

## 7. Isu yang diketahui, belum terselesaikan

- Menu sidebar yang belum diverifikasi (lihat bagian 3) — kemungkinan besar
  sebagian cuma UI kosong/placeholder, perlu dicek satu-satu sebelum diklaim
  berfungsi ke siapa pun.
- Fitur login dashboard admin — DITEMUKAN & DIPERBAIKI 6 September 2026:
  halaman `/login` (`Login.jsx`) SUDAH ADA sejak awal tapi TIDAK PERNAH
  didaftarkan ke routing (`App.jsx`) — begitu ada yang coba akses, area
  konten blank total (cuma sidebar yang muncul, karena sidebar dirender di
  luar `<Routes>`). Sudah diperbaiki: `App.jsx` sekarang render `/login`
  berdiri sendiri (tanpa Sidebar) lewat pengecekan `useLocation()`.
  `DASHBOARD_ADMIN_PASSWORD_HASH` & `SESSION_SECRET_KEY` sudah diisi di
  `.env`, `DISABLE_LOGIN_FOR_LOCAL_DEV` sudah diset `False`. **Status
  end-to-end masih perlu konfirmasi terakhir** — lihat apakah login berhasil
  setelah fix routing ini di-apply.
- Step 5 (Insight AI) dan 7 (Kirim WA) di Laboratorium pipeline masih placeholder,
  belum ada backend sama sekali.
- Belum ada `.gitignore` untuk folder backup (`talatee-backup-*/`) — sudah ada
  aturannya di `.gitignore`, tapi pastikan pola nama foldernya konsisten setiap kali
  script backup dijalankan.
- **Data Trust — SEMUA gap dari analisis awal (section 6b-6g) sudah ditutup**
  dengan versi minimal yang jujur soal batasannya masing-masing. Yang masih
  bisa dikembangkan lebih lanjut kalau ada kebutuhan nyata: business rule
  selain subtotal (konsistensi harga per produk, enum status valid), data
  lineage view yang lebih visual (grafik alur RAW → Canonical → Analytics,
  bukan cuma teks di Data Passport), dan correction untuk baris tanpa
  order_id.
- **Celah keamanan AI Agent — DITEMUKAN DAN SUDAH DIPERBAIKI (28 September
  2026)**: `AI Analyst` (chat panel dashboard, `/api/chat` → Hermes) dan
  halaman `Hermes` (iframe langsung ke UI Hermes) awalnya memanggil
  **profile Hermes yang sama persis** — tidak ada pembatasan tool sama
  sekali di sisi kita, jadi siapa pun yang chat lewat AI Analyst
  berpotensi memicu Hermes menjalankan `terminal`/`execute_code`/
  `write_file` sungguhan di laptop. Dikonfirmasi lewat dokumentasi pihak
  ketiga (fireplace-agent): prompt-approval Hermes **tidak** menggerbangi
  MCP tool calls — batas amannya harus di tool allow-list/
  `agent.disabled_toolsets`.

  **Perbaikan yang sudah dikerjakan dan diverifikasi**: dibuat profile
  Hermes baru `talatee-analyst` (blank, tidak clone dari `default`),
  `agent.disabled_toolsets` diisi 30 nama toolset (semua kecuali
  `clarify`) lewat Config → cari "disabled" → edit `comma-separated
  values`, MCP `talatee_business_data` dipasang ulang khusus di profile
  ini. Karena `gateway.multiplex_profiles` aktif, profile sekunder TIDAK
  bisa buka API server/port sendiri (dialog Channels akan selalu gagal
  SAVE untuk ini) — diakses lewat gateway bersama `default` via path
  `http://127.0.0.1:8642/p/talatee-analyst/v1/chat/completions`, dengan
  `API_SERVER_KEY` **milik profile itu sendiri** (beda dari `default`),
  yang harus ditulis manual ke `...\profiles\talatee-analyst\.env` lewat
  PowerShell (`Add-Content`) karena UI Channels menolak menyimpan key
  tanpa "enable" platform, dan "Custom Keys" di halaman Keys diam-diam
  menolak nama `API_SERVER_KEY` (dianggap key yang sudah dikenali sistem).
  `.env` Talatee (`HERMES_API_URL`/`HERMES_API_KEY`) diarahkan ke profile
  ini, bukan lagi ke `default`.

  **Verifikasi** (bukan cuma dipercaya dari config): `tool_search` di
  dalam sesi chat profile ini tidak menemukan `terminal`, `desktop_project`,
  atau toolset lain yang dimatikan; permintaan eksplisit "jalankan
  terminal: dir" ditolak dengan jujur oleh agent, dites di 3 lapis
  (chat UI Hermes, `curl` langsung ke `/p/talatee-analyst/`, dan lewat
  `/api/chat` Talatee sendiri) — dan `list_businesses` tetap berfungsi
  normal di ketiganya. Detail lengkap ada di `ARCHITECTURE.md` entri
  "Hermes AI Agent Integration" (28 September 2026).
- System prompt/persona Hermes belum disesuaikan — masih menjawab seperti
  asisten umum generik ("saya bisa bantu nulis artikel, coding, dll") kalau
  ditanya "apa yang bisa kamu bantu", belum sadar dirinya "otak" Talatee.
  Terkonfirmasi nyata (bukan cuma dugaan) waktu tes profile
  `talatee-analyst`: `reasoning_content` agent sempat bingung sendiri
  karena system prompt masih menyebut kemampuan shell yang sebenarnya
  sudah dimatikan di profile itu — tanda `SOUL.md` profile ini juga perlu
  ditulis ulang, bukan cuma toolset-nya. Direncanakan, belum dikerjakan.
- Tools/fitur AI Agent lanjutan yang diusulkan tapi SENGAJA ditunda (dinilai
  prematur untuk skala sekarang — 3 business terdaftar, 2 di antaranya
  masih data uji coba `Test Warung`/`Test Production`): `get_system_health()`,
  context-switching toolset per halaman, monitoring otonom/digest harian
  otomatis via Telegram.

## 8. Cara mulai kerja lagi dari nol (laptop baru / AI assistant baru)

1. Clone repo dari GitHub (`ashartalatee/Talatee_DataBase`)
2. Install Docker Desktop (untuk Postgres + MinIO)
3. Buat `.env` dari `.env.example`, isi dengan kredensial BARU (jangan pernah pakai
   nilai contoh di `.env.example` apa adanya — itu memang generik/placeholder)
4. `docker-compose up -d` — nyalakan Postgres & MinIO
5. Setup Python: `python -m venv venv`, aktifkan, `pip install -r requirements.txt`
6. Jalankan migrasi: `alembic upgrade head` (cek dulu command yang tepat di
   `alembic.ini`/dokumentasi Alembic project ini kalau beda)
7. Generate kredensial dashboard: `python scripts/generate_dashboard_credentials.py`,
   copy hasilnya ke `.env`
8. `uvicorn app.main:app --reload` — pastikan "Application startup complete" tanpa
   error
9. `cd dashboard && npm install && npm run dev` — buka `localhost:5173`, pastikan
   Overview menampilkan data (kalau database baru/kosong, ini akan menampilkan 0
   di semua metrik — itu wajar)

## 9. Prinsip kerja yang sudah disepakati

- **Jangan pernah hardcode kredensial di `docker-compose.yml` atau file kode apa
  pun** — selalu lewat `.env` + `${VARIABLE}`. Ini prinsip yang lahir dari insiden
  di bagian 4, jangan diulangi.
- **`.env.example` isinya SELALU placeholder generik**, tidak pernah nilai asli
  walau untuk "testing sementara".
- Kalau ragu apakah sebuah fitur di sidebar benar-benar berfungsi, **cek dulu kode/
  API-nya**, jangan asumsikan dari tampilan UI saja — banyak menu yang statusnya
  belum diverifikasi (bagian 3).
