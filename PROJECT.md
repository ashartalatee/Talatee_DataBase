# Talatee — Panduan & Konteks Proyek

Satu-satunya dokumen proyek ini. Menggantikan `ARCHITECTURE.md`,
`PROJECT_CONTEXT_TALATEE.md`, `MASTER_GUIDE.md`, `menjalankan.md`, dan
`dashboard/README.md` — lima file itu sudah tumpang tindih dan sebagian
isinya usang (menyebut menu sidebar yang sudah tidak ada, mengira Postgres
lokal itu database utama padahal bukan). File-file itu aman dihapus
setelah file ini dipakai.

## 1. Apa ini

Talatee Control Center: platform data bisnis pribadi milik Ashar (solo,
brand "Talatee Automation Lab"). Tempat menampung data dari produk-produk
vertikal (mis. Buku Kas Warung) lewat upload/API, menyimpannya rapi per
klien, dan sekarang juga punya AI Agent (Hermes) yang bisa ditanya
langsung soal data itu lewat bahasa natural.

Read-only dari sisi dashboard — semua tulis-menulis data lewat backend
API, bukan langsung ke database dari React.

## 2. Arsitektur saat ini

```
Produk satelit (Buku Kas Warung, dll)
    │  POST /ingest/upload
    ▼
FastAPI backend (Python)              uvicorn app.main:app --reload
    ├── app/config.py                 baca .env lewat pydantic_settings
    ├── app/api/routes/*.py           businesses, sources, datasets, batches,
    │                                 projects, lab_entries, auth, stats, chat
    ├── app/mcp/server.py             5 tools baca-saja untuk Hermes (lihat #4)
    ├── app/ingestion/*.py            core_processor — proses data masuk
    ├── app/models/*.py               SQLAlchemy ORM
    └── migrations/versions/*.py      Alembic
    │
    └──────────────► PostgreSQL (Neon, cloud) — lihat catatan penting di bawah
    └──────────────► MinIO (Docker lokal, port 9000/9001, bucket talatee-raw)

dashboard/ (React + Vite, port 5173)   npm run dev, fetch ke localhost:8000
    Sidebar (9 menu, rata tanpa section):
    Overview · Clients · Data Explorer · Proyek · Eksperimen ·
    AI Analyst · Hermes · Logs & Errors · Settings

Hermes (Nous Research, aplikasi desktop terpisah, 127.0.0.1:9119)
    Profile "default"       -> dipakai halaman Hermes (iframe), akses penuh
    Profile "talatee-analyst" -> dipakai AI Analyst, MCP-only, lihat #4
```

**Stack:** FastAPI (Python 3.12, `venv/`), SQLAlchemy + Alembic, PostgreSQL
(Neon), MinIO (Docker, S3-compatible), React + Vite (dashboard).

**⚠️ Database asli itu Neon (cloud), BUKAN Postgres Docker lokal.**
`docker-compose.yml` di repo ini menyalakan Postgres lokal juga (port
5434), tapi itu cuma kosong/untuk eksperimen — data client asli
(`Test Warung`, `Test Production`, dll) ada di Neon. Ini pernah bikin
bingung berjam-jam waktu setup MCP Hermes (server-nya connect ke Postgres
lokal yang kosong, bukan Neon) — kalau nanti nulis kode/config baru yang
butuh `DATABASE_URL`, **selalu cek `.env` asli**, jangan asumsikan dari
default `app/config.py`.

## 3. Cara menjalankan sehari-hari

Butuh 2 terminal (Buku Kas Warung, kalau dipakai bersamaan, terminal ke-3
— lihat repo-nya sendiri):

```powershell
# Terminal 1 — Backend Talatee
cd "D:\Talatee_Engine\TALATEE_ENGINE\Catatan Penting\Knowledge_System\02_automation_project\talatee-database"
python -m uvicorn app.main:app --reload --port 8000
```
-> `http://127.0.0.1:8000` (cek hidup: `/health`)

```powershell
# Terminal 2 — Dashboard
cd "...\talatee-database\dashboard"
npm run dev
```
-> `http://localhost:5173`

Python & Node **tidak ada di venv** — install-nya system-wide/user
(`C:\Python312\python.exe`, paket user-level). Kalau perintah `uvicorn`/
`alembic`/dll "not recognized", jalankan lewat modul: `python -m uvicorn
...`, `python -m alembic ...` (paket-nya ada, cuma scripts-nya tidak
masuk PATH).

MinIO/Postgres lokal (kalau dibutuhkan, mis. untuk Docker eksperimen):
```powershell
docker-compose up -d
```

## 4. Hermes AI Agent & AI Analyst

AI Analyst (menu dashboard) dan halaman Hermes (iframe ke 127.0.0.1:9119)
dua-duanya ngobrol dengan Hermes, tapi lewat **profile Hermes yang
berbeda** — sengaja dipisah supaya AI Analyst tidak bisa menjalankan
perintah shell/file sungguhan di laptop.

**Alur:** Dashboard -> `POST /api/chat` (backend Talatee) -> Hermes API
server (OpenAI-compatible) -> profile `talatee-analyst` -> MCP server
`app/mcp/server.py` -> database Neon.

**5 MCP tools** (`app/mcp/server.py`, paket `mcp` harus dipin `==1.30.0`
— versi 2.x menghapus class `FastMCP`):
`list_businesses`, `get_business_summary`, `query_transactions`,
`get_sales_summary`, `get_top_products`. Semua cuma baca dataset
`trust_status == "TRUSTED"` (lihat #6), dan melaporkan berapa dataset yang
dikecualikan supaya Rp0 tidak disalahartikan sebagai "tidak ada data".

**Profile `talatee-analyst`** (dibuat blank, bukan clone `default`):
- `agent.disabled_toolsets` mematikan 30 toolset (semua kecuali
  `clarify`) — terminal/file/browser/code_execution/dll semua mati.
  Diedit di Hermes: Config -> cari "disabled" -> field
  `comma-separated values`.
- MCP `talatee_business_data` dipasang khusus di profile ini juga (tiap
  profile punya konfigurasi MCP sendiri-sendiri), command/env sama
  seperti `default`.
- **Hermes pakai `gateway.multiplex_profiles`** — TIDAK ada API server
  per-profile dengan port sendiri. Profile sekunder diakses lewat gateway
  bersama `default` (port 8642) via path
  `http://127.0.0.1:8642/p/talatee-analyst/v1/chat/completions`, dengan
  `API_SERVER_KEY` **milik profile itu sendiri** (beda dari `default`).
  Dialog "Configure API server" di Channels **selalu gagal** untuk
  profile sekunder (errornya eksplisit menyuruh pindah ke `default`) —
  key harus ditulis manual:
  ```powershell
  Add-Content -Path "C:\Users\<user>\AppData\Local\hermes\profiles\talatee-analyst\.env" -Value "API_SERVER_KEY=<key>"
  ```
  (Halaman "Custom Keys" di Keys tidak bisa dipakai untuk ini — nama
  `API_SERVER_KEY` ditolak diam-diam karena sudah dikenali sistem.)
- `.env` Talatee:
  ```
  HERMES_API_URL=http://127.0.0.1:8642/p/talatee-analyst
  HERMES_API_KEY=<key di atas>
  ```
- **`PYTHONDONTWRITEBYTECODE=1`** wajib ada di env MCP server — tanpa
  ini, `uvicorn --reload` mendeteksi file `.pyc` yang ditulis Python di
  `app/mcp/__pycache__/` sebagai "perubahan kode" dan restart sendiri di
  tengah request (gejala: "Failed to fetch" random di AI Analyst).

**Verifikasi keamanan sudah dites 3 lapis** (`tool_search` di sesi chat,
`curl` langsung ke `/p/talatee-analyst/`, `curl` ke `/api/chat` Talatee
sendiri) — permintaan `terminal` ditolak di ketiganya, `list_businesses`
tetap berfungsi normal di ketiganya.

**Belum dikerjakan:** `SOUL.md` profile `talatee-analyst` belum ditulis
— persona-nya masih generik/warisan `default`, sempat kelihatan bingung
di `reasoning_content` karena system prompt menyebut kemampuan shell yang
sebenarnya sudah dimatikan.

## 5. Data Trust (`trust_status`)

Prinsip: **analitik/insight cuma boleh baca dataset yang sudah TRUSTED**
(Data Trust Spec Rule 06). Dataset baru masuk berstatus belum-trusted,
harus lewat pipeline validasi (halaman Eksperimen: Ambil Data -> Bersihkan
-> Validasi -> Analisis) sebelum dipromosikan. Fitur pendukung yang sudah
ada: dedup lintas-batch (`core_processor.py`), validasi `qty x
harga_satuan = subtotal`, Correction Model (untuk baris tanpa `order_id`),
Reconciliation, Data Passport (lineage RAW -> Canonical -> Analytics).

## 6. Keamanan & rahasia

**Insiden yang pernah terjadi (3 September 2026, sudah ditangani):** repo
ini publik, dan `.env.example` sempat berisi kredensial ASLI (bukan
placeholder) — password Postgres/MinIO `talatee`/`talatee123`. Sudah
diganti di sumbernya (bukan cuma file config), `docker-compose.yml`
sekarang baca dari `${VARIABLE}`, bukan hardcode. **Password lama itu
tetap ada di git history selamanya** — jangan pernah pakai
`talatee`/`talatee123` untuk apa pun lagi di project ini.

**Prinsip yang berlaku sejak itu:**
- Tidak pernah hardcode kredensial di `docker-compose.yml`/kode apa pun —
  selalu `.env` + `${VARIABLE}`.
- `.env.example` isinya SELALU placeholder generik, tidak pernah nilai
  asli walau "testing sementara".
- Sebelum commit, selalu `git status`/`git diff` dulu, jangan `git add .`
  langsung — cek satu-satu, terutama kalau ada file baru yang tidak
  dikenali asalnya.

**Yang TIDAK BOLEH masuk GitHub** (sudah di `.gitignore`): `.env`/
`.env.local` (password & API key), `talatee.sqlite` (data transaksi
asli), `node_modules/`/`venv/` (bisa di-generate ulang), isi Docker
volume Postgres/MinIO (data operasional, bukan kode).

**Disimpan di tempat KETIGA** (bukan git, bukan folder biasa — password
manager/catatan aman): password Postgres/MinIO, `TALATEE_API_KEY` (dari
`scripts/create_api_key.py`, plaintext cuma muncul sekali), `API_SERVER_KEY`
Hermes (lihat #4), `HERMES_API_KEY`.

## 7. Deploy Vercel

Project `talatee-dashboard` (bukan `talatee-data-base` — itu project lain
yang salah, men-deploy backend Python, dibiarkan tidak terpakai).
Settings yang WAJIB benar (Settings -> Build and Deployment):
- **Root Directory**: `dashboard` (bukan `./` — root repo isinya backend
  Python, bukan kode React)
- **Framework Preset**: `Vite` (bukan `Other` — biar Build/Output/Install
  Command otomatis benar, jangan di-override manual)

Kalau setelah ganti setting ini tampilannya masih belum update, redeploy
manual dulu (Deployments -> titik tiga -> Redeploy) — ganti Project
Settings saja tidak otomatis trigger build ulang.

## 8. Backup & pindah laptop

Data Postgres/MinIO Docker lokal cuma ada di harddisk laptop ini — tapi
**data client asli ada di Neon (cloud)**, jadi tidak akan hilang kalau
laptop rusak (beda dari asumsi lama waktu masih full-lokal). Yang tetap
perlu di-backup manual: isi MinIO lokal kalau dipakai, dan `.env` (catat
ke password manager, JANGAN taruh di folder backup data).

```powershell
.\scripts\backup.ps1     # kalau masih pakai data lokal
.\scripts\restore.ps1 -BackupFolder "..."
```

**Pindah ke laptop baru (ringkas):** install Python 3.12+/Node.js/Docker/
Git -> `git clone` repo -> buat ulang `.env` dari password manager ->
`pip install -r requirements.txt` -> `alembic upgrade head` (Neon, bukan
lokal, jadi biasanya sudah sinkron) -> `uvicorn ...` -> `cd dashboard &&
npm install && npm run dev` -> setup ulang profile Hermes `talatee-analyst`
kalau AI Analyst mau dipakai (lihat #4, ini yang paling panjang).

## 9. Isu yang diketahui, belum selesai

- **System prompt/`SOUL.md` Hermes** belum disesuaikan — lihat #4.
- **Fitur yang ADA tombolnya di sidebar tapi belum diverifikasi jalan**:
  cek dulu kode/API-nya sebelum berasumsi, jangan percaya tampilan UI
  saja.
- **Tools AI Agent lanjutan yang sengaja ditunda** (dinilai prematur untuk
  skala sekarang — 3 business terdaftar, 2 di antaranya masih data uji
  coba): `get_system_health()`, context-switching toolset per halaman,
  monitoring otonom/digest harian otomatis via Telegram.
- **Login dashboard admin** (`auth.py`, `Login.jsx`) ada di codebase tapi
  belum pernah didemonstrasikan/dites end-to-end — test dulu alurnya dari
  awal sebelum diandalkan.
- Business rule selain subtotal (konsistensi harga per produk, enum
  status valid), data lineage view yang lebih visual, correction untuk
  baris tanpa `order_id` — semua bisa dikembangkan lebih lanjut kalau ada
  kebutuhan nyata, belum mendesak.

## 10. Troubleshooting cepat

| Gejala | Penyebab | Solusi |
|---|---|---|
| `'uvicorn'/'alembic'/dll' is not recognized` | Scripts tidak ada di PATH (bukan venv, install-nya user-level) | `python -m uvicorn ...` / `python -m alembic ...` |
| `ECONNREFUSED ::1:8000` dari produk satelit | URL masih `localhost`, Windows resolve ke IPv6 | Ganti ke `http://127.0.0.1:8000` |
| `Connection refused` port 5434 (Postgres lokal) | Docker Desktop belum jalan/container mati | `docker-compose up -d` (cuma perlu kalau pakai fitur yang butuh Postgres lokal, data asli ada di Neon) |
| Dashboard `localhost:5173` blank/`ERR_CONNECTION_REFUSED` | `npm run dev` di folder `dashboard` belum jalan | `cd dashboard && npm run dev` |
| AI Analyst "Failed to fetch" random | `uvicorn --reload` restart sendiri gara-gara `.pyc` di `app/mcp/__pycache__/` | Pastikan `PYTHONDONTWRITEBYTECODE=1` ada di env MCP server (lihat #4) |
| MCP tools bilang business "tidak ditemukan" padahal ada | `DATABASE_URL` yang dipakai MCP server nunjuk ke Postgres lokal kosong, bukan Neon | Isi `DATABASE_URL` eksplisit di env MCP server, ambil dari `.env` asli |
| Vercel 404 padahal push sudah masuk | Root Directory/Framework Preset salah | Lihat #7 |

## 11. Prinsip kerja

1. **Raw data tidak pernah ditimpa** — upload file yang sama 2x = 2 batch
   terpisah, bukan 1 batch yang di-overwrite. Bukan bug.
2. **Kode != Data.** Kode di GitHub. Data asli di Neon (bukan lokal lagi).
   Jangan pernah dicampur.
3. **Analitik/AI Agent cuma boleh baca dataset TRUSTED** — jangan pernah
   bikin fitur yang diam-diam melewati aturan ini.
4. **Sebelum expose fitur AI Agent ke orang lain**, pastikan pembatasan
   tool-nya (profile `talatee-analyst`) masih aktif dan terverifikasi —
   jangan asumsikan dari config saja, tes perilakunya langsung.
5. Kalau ragu apakah sebuah fitur di sidebar benar-benar berfungsi, cek
   kode/API-nya, jangan asumsikan dari tampilan UI.

## 12. Riwayat ringkas

Dokumen sejarah lengkap (progress tracker awal, detail Phase 1, dll) tidak
disimpan di sini karena sudah tidak relevan untuk kerja ke depan — yang
tersisa cuma poin pentingnya:

- **23 Agu 2026** — Dashboard React Phase 2 v1 jalan pertama kali (Overview,
  Upload).
- **24 Agu 2026** — Fitur Businesses (multi-klien) + integrasi Buku Kas
  Warung sebagai produk vertikal pertama.
- **25 Agu 2026** — Auth API key untuk endpoint ingest.
- **3 Sep 2026** — Insiden kebocoran kredensial di `.env.example`,
  ditangani (lihat #6).
- **4–5 Sep 2026** — Data Trust: `trust_status`, dedup, validasi business
  rule, Correction Model, Reconciliation, Data Passport.
- **28 Sep 2026** — Integrasi Hermes AI Agent: MCP server, `/api/chat`,
  panel AI Analyst, redesign navbar (15→9 item) & Overview.
- **28 Sep 2026** — Celah keamanan AI Agent ditemukan & ditutup (profile
  `talatee-analyst` terbatas).
- **30 Sep 2026** — Deploy Vercel diperbaiki (Root Directory & Framework
  Preset).
