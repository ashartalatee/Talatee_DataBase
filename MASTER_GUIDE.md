# TALATEE — Panduan Master

> Dokumen ini jawaban lengkap untuk 4 pertanyaan: **apa ini, bagaimana cara kerjanya,
> bagaimana menjalankannya sehari-hari, dan bagaimana memindahkannya ke laptop baru.**
> Baca dari atas ke bawah kalau bingung soal apa pun terkait project ini secara keseluruhan.

---

## 1. Gambaran Besar — Apa Ini Sebenarnya?

Ini **bukan satu aplikasi**, tapi **dua sistem terpisah yang saling terhubung**:

```
+---------------------------+         +--------------------------------------+
|   BUKU KAS WARUNG          |         |         TALATEE                       |
|   (produk vertikal)         |         |   (command center / platform)          |
|                              |         |                                         |
|   Next.js + SQLite            |  sync   |   FastAPI + Postgres + MinIO             |
|   Laporan warung,               |--API--> |   Command center: pantau SEMUA          |
|   WhatsApp, dashboard              key    |   klien dari 1 dashboard                 |
|   internal warung                 |       |                                         |
+---------------------------+         +--------------------------------------+
     Datanya: 1 warung                    Datanya: SEMUA klien
     (nanti bisa banyak produk              (Buku Kas Warung, dan produk
      serupa: klinik, resto, dll)            vertikal lain di masa depan)
```

**Analogi paling gampang:** Buku Kas Warung itu seperti kasir di satu toko cabang — dia
punya pembukuan sendiri, laporan sendiri, WhatsApp bot sendiri, khusus buat pemilik warung
itu. Talatee itu **kantor pusat** — setiap kali kasir di cabang mana pun (warung, nanti
klinik, nanti resto) mencatat sesuatu, salinannya otomatis terkirim ke kantor pusat, supaya
kamu (sebagai pemilik/pengelola semua bisnis itu) bisa pantau semuanya dari satu layar.

### Kenapa dipisah, bukan digabung jadi satu aplikasi?
1. **Buku Kas Warung** dipakai LANGSUNG oleh pemilik warung (butuh UX simpel, laporan
   WhatsApp, dll — spesifik banget buat warung).
2. **Talatee** dipakai OLEH KAMU untuk memantau semua bisnis yang kamu kelola sekaligus.
3. Kalau digabung, setiap kamu bikin produk vertikal baru (Buku Kas Klinik, dst), kamu harus
   rombak ulang semuanya. Dengan dipisah + terhubung API, produk baru tinggal "nyambung" ke
   Talatee tanpa mengubah Talatee sama sekali.

---

## 2. Cara Kerja — Alur Data dari Awal Sampai Akhir

1. Pemilik warung buka **Buku Kas Warung** (`localhost:3000`), upload CSV transaksi harian.
2. Buku Kas Warung memproses data itu **secara lokal** — validasi, deteksi duplikat, koreksi
   (ini semua logic yang sudah ada sebelum kita sentuh apa pun, disimpan di database
   `talatee.sqlite` miliknya sendiri).
3. **Setelah** proses lokal itu sukses, ada 1 langkah tambahan (yang kita bangun): Buku Kas
   Warung kirim **salinan file mentah** yang sama ke Talatee, lewat internet/API
   (`POST /ingest/upload`), dengan menyertakan **API key** sebagai bukti "ini request sah
   dari Buku Kas Warung, bukan orang asing".
4. Talatee terima file itu, simpan:
   - **File aslinya** (bytes CSV/Excel) -> **MinIO** (object storage, khusus buat file)
   - **Catatan tentang file itu** (siapa upload, kapan, berapa baris, dst) -> **Postgres**
     (database, khusus buat data terstruktur/metadata)
5. Kalau Talatee lagi mati/tidak bisa dihubungi, langkah 3-4 gagal **tapi Buku Kas Warung
   tetap sukses seperti biasa** buat pemilik warungnya — cuma masuk catatan error di log,
   tidak mengganggu pemilik warung sama sekali. (Ini sudah dites beneran jalan.)
6. Kamu buka **dashboard Talatee** (`localhost:5173`) — bisa lihat semua warung/klien,
   dikelompokkan per kategori (Warung, Klinik, Resto, dst), semua datanya baca langsung dari
   Postgres+MinIO di atas.

### Kenapa raw file & metadata dipisah (MinIO vs Postgres)?
Postgres itu database yang dioptimasi buat data terstruktur kecil-kecil (baris, kolom, angka).
Kalau file CSV/Excel gede-gede ditumpuk di situ, database jadi lambat dan susah di-backup.
MinIO itu khusus buat nyimpen file — makanya dipisah. Prinsipnya: **Postgres tahu "file ini
ADA dan isinya kira-kira apa", MinIO nyimpen "isi filenya yang sebenarnya".**

---

## 3. Komponen & Di Mana Mereka "Hidup"

| Komponen | Teknologi | Kodenya di mana | Datanya di mana |
|---|---|---|---|
| Backend Talatee | Python + FastAPI | folder `talatee-data-platform/app/` | - |
| Dashboard Talatee | React + Vite | folder `talatee-data-platform/dashboard/` | - |
| Database metadata | PostgreSQL | (jalan lewat Docker) | Docker volume `postgres_data` |
| Object storage | MinIO | (jalan lewat Docker) | Docker volume `minio_data` |
| Buku Kas Warung | Next.js + TypeScript | folder `buku-kas-warung/` | - |
| Database lokal warung | SQLite | - | file `buku-kas-warung/talatee.sqlite` |

**Poin penting:** kolom "Kodenya di mana" itu yang masuk **GitHub**. Kolom "Datanya di mana"
itu **TIDAK PERNAH masuk GitHub** — itu urusan backup terpisah (lihat bagian 6).

---

## 4. Cara Menjalankan Sehari-hari (di laptop ini)

Butuh **3 terminal** jalan bersamaan:

### Terminal 1 — Backend Talatee
```powershell
cd "D:\Talatee_Engine\...\talatee-database"
.\venv\Scripts\Activate.ps1
docker compose up -d
uvicorn app.main:app --reload
```
-> `http://127.0.0.1:8000` (API), `http://127.0.0.1:8000/docs` (Swagger UI)

### Terminal 2 — Dashboard Talatee
```powershell
cd "D:\Talatee_Engine\...\talatee-database\dashboard"
npm run dev
```
-> `http://localhost:5173`

### Terminal 3 — Buku Kas Warung
```powershell
cd [folder buku-kas-warung]
npm run dev
```
-> `http://localhost:3000`

**Urutan penting:** Terminal 1 harus jalan DULUAN dan tetap hidup sebelum kamu upload apa pun
di Terminal 3 — kalau tidak, sync ke Talatee akan gagal (walau Buku Kas Warung sendiri tetap
baik-baik saja).

---

## 5. Apa yang Masuk GitHub, Apa yang TIDAK

### MASUK GitHub (2 repo terpisah)
- **Repo `talatee-data-platform`**: seluruh isi folder ini KECUALI yang di `.gitignore`
  (kode Python, kode React dashboard, `ARCHITECTURE.md`, migrations, scripts)
- **Repo `buku-kas-warung`**: seluruh isi folder ini KECUALI yang di `.gitignore` (kode
  Next.js, termasuk `lib/talatee-core/` dan `lib/talatee-bridge/`)

### TIDAK BOLEH masuk GitHub (sudah dikecualikan lewat `.gitignore`, penting dipahami KENAPA)
| File/folder | Kenapa jangan |
|---|---|
| `.env`, `.env.local` | Isinya password database & API key — kalau bocor ke GitHub (walau private), siapa pun yang pernah lihat repo bisa pakai |
| `talatee.sqlite` | Data transaksi ASLI klien warung — bukan kode, dan sensitif |
| `node_modules/`, `venv/` | Bisa di-generate ulang dari `package.json`/`requirements.txt`, buang-buang tempat kalau ikut di-commit |
| Isi Docker volume (Postgres/MinIO) | Ini DATA operasional yang terus berubah tiap hari — git bukan tempat yang tepat buat ini (lihat bagian 6) |

### Disimpan di tempat KETIGA (bukan git, bukan folder biasa) — password manager / catatan aman
- Password Postgres (`talatee`/`talatee`, dari `docker-compose.yml` — untuk sekarang OK
  karena cuma lokal, tapi kalau nanti di-hosting online HARUS diganti jadi random)
- Password MinIO (`talatee`/`talatee123`)
- Isi `TALATEE_API_KEY` yang di-generate lewat `scripts/create_api_key.py` (plaintext-nya
  cuma muncul SEKALI — begitu hilang, harus generate baru & update `.env.local`)

---

## 6. Backup Data (WAJIB dilakukan rutin, bukan cuma pas mau ganti laptop)

Data di Postgres & MinIO itu cuma ada di **harddisk laptop ini** (lewat Docker volume) —
tidak otomatis ke mana-mana. Kalau laptop rusak/hilang/diganti tanpa backup, **data hilang
permanen**.

### Cara backup (sudah disiapkan script-nya)
```powershell
cd "D:\Talatee_Engine\...\talatee-database"
.\scripts\backup.ps1
```
Ini bikin folder baru `talatee-backup-2026-08-26_1000\` berisi salinan lengkap Postgres +
MinIO. **Setelah itu, WAJIB** copy folder itu ke Google Drive / hardisk eksternal / cloud
storage lain — kalau cuma didiamkan di laptop yang sama, backup ini juga ikut hilang kalau
laptopnya rusak.

**Rutinitas yang disarankan:** jalankan `backup.ps1` tiap kali sudah ada data penting baru
masuk (misal habis onboarding klien baru), minimal seminggu sekali kalau sudah jalan rutin.

---

## 7. Cara Pindah ke Laptop Baru (Lengkap, Berurutan)

### Di laptop LAMA (sebelum pindah)
1. Jalankan `.\scripts\backup.ps1` — dapatkan folder backup terbaru
2. Copy folder backup itu ke Google Drive/hardisk eksternal/USB
3. Pastikan kode sudah ter-push ke GitHub (`git push`) di kedua repo
4. Catat/salin isi `.env` (Talatee) dan `.env.local` (buku-kas-warung) ke password manager
   — **JANGAN** ikut taruh di folder backup data, simpan terpisah

### Di laptop BARU
1. Install prasyarat: Python 3.11+, Node.js, Docker Desktop, Git
2. Clone kedua repo dari GitHub:
   ```
   git clone <url-repo-talatee-data-platform>
   git clone <url-repo-buku-kas-warung>
   ```
3. **Talatee**: buat ulang `.env` (isi dari password manager yang dicatat tadi), lalu:
   ```
   cd talatee-data-platform
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   docker compose up -d
   ```
4. **Restore data** — copy folder backup dari Google Drive/USB ke laptop baru, lalu:
   ```
   .\scripts\restore.ps1 -BackupFolder "C:\path\ke\talatee-backup-2026-08-26_1000"
   ```
5. Jalankan `alembic upgrade head` untuk mastiin skema database sinkron dengan kode terbaru
6. Jalankan backend (`uvicorn app.main:app --reload`) — cek `localhost:8000/health`
7. **Dashboard**: `cd dashboard`, `npm install`, `npm run dev`
8. **Buku Kas Warung**: buat ulang `.env.local` (isi dari password manager), lalu
   `npm install`, `npm run dev`
9. Test: upload 1 file di Buku Kas Warung, cek muncul di dashboard Talatee — kalau sukses,
   migrasi selesai total.

---

## 8. Troubleshooting Cepat (masalah yang pernah kejadian, biar tidak nanya ulang)

| Gejala | Penyebab | Solusi |
|---|---|---|
| `'uvicorn'/'alembic'/'pytest' is not recognized` | venv belum aktif | `.\venv\Scripts\Activate.ps1` dulu, pastikan `(venv)` muncul di prompt |
| `ECONNREFUSED ::1:8000` di log buku-kas-warung | `TALATEE_API_URL` masih `localhost`, Windows resolve ke IPv6 | Ganti ke `http://127.0.0.1:8000` di `.env.local`, restart `npm run dev` |
| `Connection refused` port 5434 (Postgres) | Docker Desktop belum jalan / container mati | `docker compose up -d` |
| `[talatee-sync] Talatee menolak sync (401)` | API key salah/kosong/file `sync.ts` versi lama | Cek `TALATEE_API_KEY` di `.env.local`, cek `sync.ts` ada baris `Authorization` |
| Dashboard `localhost:5173` blank/`ERR_CONNECTION_REFUSED` | `npm run dev` di folder `dashboard` belum/tidak jalan | `cd dashboard`, `npm run dev` |

---

## 9. Prinsip yang Jangan Dilupakan

1. **Raw data tidak pernah ditimpa** — upload file yang sama 2x = 2 batch terpisah, bukan
   1 batch yang di-overwrite. Ini bukan bug.
2. **Kode != Data.** Kode di GitHub. Data di backup terpisah. Jangan pernah dicampur.
3. **Gagal sync ke Talatee tidak boleh mengganggu Buku Kas Warung.** Prinsip ini sudah dites
   nyata — kalau suatu saat ada perubahan kode, pastikan prinsip ini tetap terjaga.
4. **`talatee-level1-package` sudah selesai perannya** (template yang sudah di-copy) — kalau
   nanti bikin produk vertikal kedua, di situ baru waktunya evaluasi bikin `talatee-core`
   jadi package/repo terpisah yang reusable.
