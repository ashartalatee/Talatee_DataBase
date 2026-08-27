# Talatee Data Hub — Dashboard (Phase 2 v1)

Dashboard React untuk memvisualisasikan data di Talatee Personal Big Data Platform.
Read-only — semua data dibaca dari API backend (`talatee-data-platform`), tidak ada
tulis-menulis langsung ke database dari sini.

## Cara Menjalankan

Pastikan backend (`app/`, di folder induk) sudah jalan dulu:

```
# di root project talatee-data-platform, folder terpisah dari dashboard/
docker compose up -d
uvicorn app.main:app --reload
```

Backend harus bisa diakses di `http://localhost:8000` (dicek: buka `localhost:8000/health`).

Baru jalankan dashboard-nya:

```
cd dashboard
npm install
npm run dev
```

Buka `http://localhost:5173`.

## Halaman

- **Overview** (`/`) — ringkasan: total records, datasets, sources, storage, breakdown per
  source, dan daftar batch terbaru.
- **Sources** (`/sources`) — daftar semua source + detail dataset per source.
- **Datasets** (`/datasets`) — daftar semua dataset (kartu) + detail schema & riwayat batch.
- **Jobs** (`/jobs`) — daftar semua batch ingestion + detail (termasuk file & tombol download).
- **Storage** (`/storage`) — total storage terpakai + breakdown records per source.

## Struktur

```
dashboard/
├── src/
│   ├── api/client.js      # semua panggilan ke backend API, satu tempat
│   ├── lib/
│   │   ├── format.js      # formatting angka/tanggal/status
│   │   └── useFetch.js    # hook fetch + loading/error state
│   ├── components/         # Sidebar, StatCard, StatusBadge, States (loading/error/empty)
│   ├── pages/               # satu file per halaman
│   ├── App.jsx              # routing
│   └── index.css            # design tokens (warna, font) via Tailwind v4 @theme
```

## Kalau mau nambah halaman/fitur baru

1. Kalau butuh data baru dari backend yang belum ada endpoint-nya, tambah dulu route di
   `app/api/routes/` (backend), baru tambah fungsi di `src/api/client.js`.
2. Buat file baru di `src/pages/`, daftarkan route-nya di `src/App.jsx`.
3. Kalau perlu link navigasi baru di sidebar, tambah di `src/components/Sidebar.jsx`.

## Di luar scope v1 (belum ada backend-nya)

- Halaman Schemas, Logs, Settings — placeholder di infografik awal, backend belum mendukung.
- Cleaning/Analysis/AI Agent — itu Phase 5/6, bukan bagian dashboard ini.
