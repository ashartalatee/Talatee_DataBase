# Revisi setelah laporan M0

Berlaku bersama `prompt-agent-tahap-1.md`. **Jika ada pertentangan, file ini yang menang.**
Alasannya: laporan M0 menunjukkan beberapa asumsi di prompt awal tidak cocok dengan kode yang sudah ada. Prinsip revisi ini: **perluas yang sudah ada, jangan membuat sistem kedua.**

## A. Fakta dari M0 yang menjadi dasar

1. FastAPI berjalan lokal di Windows; PostgreSQL di Neon (cloud); MinIO di Docker lokal; dashboard di Vercel. Penonton di internet tidak bisa menjangkau backend lokal.
2. `ApiKey` **tidak terikat ke bisnis**. Saat upload, bisnis ditentukan dari field `business_name` dan **dibuat otomatis** bila belum ada.
3. Kepercayaan (`trust_status`) ada di level **Dataset**, bukan file. Dataset adalah wadah rangkaian Batch; satu Source (channel) memiliki Dataset; satu Batch memiliki satu File.
4. Dedup ada di level aplikasi per `dataset_id` (`order_id`, atau `transaction_ref|product_name`); kebijakannya "kejadian terakhir menang". Tidak ada constraint UNIQUE di database.
5. Sistem **sudah punya** lapisan Bersih, Karantina, dan rekonsiliasi (`clean_rows.py`, `issue_checks.py`, `BatchCleanView.jsx`: Asli = Bersih + Karantina + Dibuang), dan model `Correction` (koreksi manual yang diterapkan `core_processor`).
6. `core_processor` sudah memeriksa `qty × harga = subtotal`, tanggal, dan status omzet.
7. MCP: 5 tool, semuanya read-only dan hanya data TRUSTED. Interaksi Hermes **tidak dicatat**. Hermes lokal, sehingga chat publik tidak mungkin dan tidak boleh dibuat.
8. Simulator saat ini skrip lokal yang hanya mau ke localhost, dan guard demo-nya hanya cek teks "demo" pada nama bisnis.

## B. M0b: pertanyaan penutup (tanpa mengubah kode)

Jawab ringkas, dengan nama file/fungsi:

1. Nilai persis enum `trust_status` (grep di model dan migrasi). Laporan pertama menyebut empat nilai termasuk `VALIDATING`, laporan terakhir tiga nilai; mana yang benar? Pemetaan ke status di prototipe: Baru masuk, Siap diverifikasi, Perlu ditinjau, Ditahan, Terpercaya.
2. Bagaimana Dataset ditentukan saat upload (per source, per nama file, atau lainnya)? Apa yang terjadi pada `trust_status` saat Batch baru masuk ke Dataset yang sudah TRUSTED (lihat trust-reset)?
3. **Tabel per aturan**: untuk setiap aturan di bagian 3 prompt tahap 1 (ganda, tanggal tidak valid/masa depan, batal/retur, qty, subtotal, nilai ekstrem, subtotal ≠ qty × harga, perapian kategori, format `Rp`, stok, marketing, katalog), tulis: sudah ada / sebagian / belum, beserta file dan fungsinya. Jelaskan juga kapan baris masuk Karantina, dan apakah ada ambang persentase.
4. Bagaimana `Correction` bekerja (siapa membuat, bagaimana diterapkan, apakah tercatat/dapat dibatalkan).
5. Dua opsi desain untuk unit "tahan / bersihkan / verifikasi" di Gudang Data, lengkap dengan dampak dan rekomendasimu:
   - **Opsi A:** memakai lapisan yang ada. Penahanan di level Batch (Batch di bawah ambang tidak ditulis ke core), verifikasi di level Dataset.
   - **Opsi B:** untuk bisnis demo, satu upload = satu Dataset, sehingga tahan/bersihkan/verifikasi per file seperti di prototipe.
6. Usulan pengikatan API key ke bisnis (kolom `api_keys.business_id` nullable) dan jalur upload khusus demo.
7. Daftar tempat yang akan terpengaruh `is_demo`: Overview, Clients, Data Explorer, tool MCP, stats.

**Selesai bila:** Ashar menyetujui jawaban dan memilih opsi A atau B.

## C. Revisi M1

- `is_demo` **hanya di tabel `businesses`** (satu sumber kebenaran). Dataset, Source, dan Batch mewarisinya lewat relasi. Jangan menambahkannya di tabel lain kecuali ada alasan kuat yang kamu laporkan.
- **Pengikatan API key:** migrasi `api_keys.business_id` (nullable). Bila terisi, upload dengan key itu dipaksa ke bisnis tersebut dan `business_name` dari klien diabaikan atau ditolak bila berbeda. Key demo dibuat oleh skrip seed dan terikat ke bisnis demo. Perilaku key lama (tanpa `business_id`) tidak berubah.
- **Endpoint pemilik** (sesi dashboard, bukan publik), semuanya memaksa bisnis demo di sisi server:
  - `POST /showcase/demo/upload` (banyak file; mengabaikan `business_name` dari klien)
  - `POST /showcase/simulator/trigger` (satu batch demo)
  - `POST /showcase/reset` (pratinjau jumlah → konfirmasi → hapus; hanya bisnis `is_demo`, objek MinIO bisnis itu saja; ikuti pola `deletion_log` yang ada)
- **Refactor simulator** menjadi service (`app/services/demo_simulator_service.py`) yang memanggil `IngestionEngine` langsung; skrip CLI tetap ada sebagai pembungkus. Guard berbasis `is_demo`, bukan teks nama.
- **Efek `is_demo` pada agregat:** agregat **lintas bisnis** (Overview total, daftar default) mengecualikan bisnis demo. Namun tool MCP **tetap bisa** menjawab untuk bisnis demo bila bisnis itu dipilih secara eksplisit (kalau tidak, Hermes tidak bisa menjawab untuk Panggung). Bisnis demo diberi lencana "Demo" di Clients.
- Tes: key terikat tidak bisa menulis ke bisnis lain; `business_name` palsu ditolak; reset hanya menyentuh bisnis demo; agregat lintas bisnis mengecualikan demo; MCP menjawab bisnis demo bila dipilih eksplisit; seed idempoten.

## D. Revisi M2 dan M3 (menggantikan rancangan awal)

**M2: aturan kualitas, dengan memperluas modul yang ada.**
- Berdasarkan tabel per aturan di M0b. Aturan yang sudah ada **tidak diduplikasi**. Aturan baru ditaruh di `issue_checks.py`, `clean_rows.py`, atau `core_processor`; `app/services/business_rules.py` hanya dibuat bila memang tidak ada tempat yang cocok.
- Tambahan yang diperlukan (bila belum ada): adapter header (peta alias kolom), deteksi domain, perbaikan otomatis (format `Rp`, format tanggal, huruf kategori), persentase lolos dengan ambang 70% (batal/retur tidak dihitung sebagai kegagalan), alasan per baris, deteksi file kembar lewat checksum yang sudah ada di tabel `files`.
- **Dedup:** pertahankan kebijakan yang ada (kejadian terakhir menang per dataset). Jangan menambahkan penolakan lintas file. Tambahkan hanya **peringatan** bila kunci yang sama muncul di dataset lain milik bisnis yang sama, agar tidak terhitung ganda di Overview tanpa disadari.
- **Domain baru** (stok, marketing, katalog): tabel core baru per domain (`core_stock_snapshots`, `core_marketing_daily`, `core_product_catalog`), semuanya membawa `dataset_id`, sehingga gerbang TRUSTED berlaku lewat join. Penjualan tetap memakai `CoreTransaction`. Aturan per domain mengikuti bagian 3 prompt tahap 1.
- **Ditahan:** persentase lolos < 70% → tidak bisa dipromosikan ke TRUSTED, lewat mekanisme sesuai opsi A/B yang dipilih. Penolakan terjadi di service, bukan hanya UI. Penanda "ditahan otomatis" memakai kolom baru bersifat nullable (alasan + waktu), **tanpa mengubah enum status**.

**M3: pembersihan lewat lapisan yang sudah ada** (tidak membuat dataset `-bersih` bila opsi A):
1. Perbaikan deterministik tambahan masuk ke `clean_rows.py` (format `Rp`, tanggal, huruf kategori).
2. Baris yang tidak bisa diperbaiki masuk **Karantina** dengan alasan yang jelas.
3. "Hitung ulang subtotal dari qty × harga" **tidak** otomatis; ia dibuat sebagai **Correction** beralasan ("mengandalkan asumsi qty dan harga benar"), opsional, tercatat, dan bisa dibatalkan.
4. **Pratinjau dry-run:** endpoint yang mengembalikan sebelum/sesudah, baris yang masuk Karantina beserta alasan, dan "N dari M baris layak berhasil diselamatkan (X%)", **tanpa menulis apa pun**. Penerapan memakai jalur yang sama setelah konfirmasi.
5. Jika yang bisa diselamatkan < 70% baris layak, penerapan ditolak dengan pesan agar meminta file yang benar dari sumbernya.
6. Tidak ada imputasi atau nilai yang dikarang.

## E. Revisi M5: topologi dan keamanan Panggung

- Backend berjalan lokal. **Jangan membuka tunnel publik ke seluruh FastAPI.** Itu akan ikut membuka endpoint upload dan login.
- Tahap sekarang: Panggung dijalankan dari laptop Ashar (localhost atau dev tunnel pribadi) dan **dibagikan lewat berbagi layar/rekaman**. Penonton tidak mengakses backend.
- `/public/stage/summary` tetap dibuat sesuai spesifikasi (hanya GET, hanya SELECT, hanya bisnis demo, tanpa nama file, tanpa rahasia), tetapi dipasang di balik flag konfigurasi `STAGE_PUBLIC_ENABLED` dengan nilai awal **false**. Bila false, endpoint hanya melayani sesi dashboard.
- Tautan publik yang bisa dibuka siapa saja ditunda. Opsi untuk nanti: backend menulis **snapshot JSON statis** ke penyimpanan publik setelah data berubah, sehingga penonton tidak pernah menyentuh backend.
- `ShowcaseControl` (Simulator, Reset, Upload demo) tetap hanya di balik sesi admin dan tidak pernah muncul di `/stage`.

## F. Yang tetap berlaku dari prompt awal

Aturan kerja (bagian 1), milestone M6 (log Hermes + tool MCP stok/kampanye/channel, tanpa chat publik), spesifikasi bentuk respons ringkasan (bagian 4), dan batas keamanan (bagian 5). Tampilan Gudang Data (M4) menyesuaikan opsi A/B: unit yang ditampilkan adalah Batch/File dalam Dataset, dan verifikasi dilakukan pada unit yang dipilih di M0b.
