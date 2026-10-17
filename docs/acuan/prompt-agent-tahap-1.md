# Prompt agent, Tahap 1: Panggung + Gudang Data (brand demo "Talatee Skincare")

Tempel seluruh isi file ini ke agent (Antigravity), lalu minta ia mengerjakan **Milestone 0 saja** dulu.
Lampirkan juga file `panggung-prototipe-acuan.html` ke folder repo (mis. `docs/acuan/`) agar bisa dibaca agent.

---

## 0. Konteks

- Pemilik: Ashar. Repo: `talatee-database` (FastAPI + PostgreSQL + MinIO + Alembic + pytest; dashboard React di Vercel). Lingkungan: Windows, PowerShell, `.\venv\Scripts\pytest`.
- Tujuan: memindahkan **prototipe** Panggung + Gudang Data menjadi fitur yang benar-benar berjalan di sistem ini, supaya Ashar bisa memakainya sehari-hari dan memperagakannya di konten.
- **Talatee Skincare adalah brand demo, bukan data client.** Menjual di TikTok Shop, Shopee, Lazada, WhatsApp, dan Website. Domain data: Penjualan, Stok, Marketing, Katalog SKU.
- Dua lapisan yang harus terpisah:
  - **Control Center** (belakang panggung, hanya Ashar): upload, Gudang Data, verifikasi, pembersihan, reset, simulator.
  - **Panggung** (`/stage`, bisa dilihat penonton): hanya membaca ringkasan data demo yang sudah terpercaya.
- Panggung **tidak boleh** menampilkan kata "Control Center", "Kompas", nama menu internal, nama tabel/route internal, atau nama file asli. Kata "Talatee Skincare" (brand demo) boleh.
- Prinsip sistem yang sudah ada dan **tidak boleh dilanggar**:
  1. Data baru masuk ke Eksperimen dulu. Hanya dataset `TRUSTED` yang boleh dihitung di Overview, Clients, Data Explorer, dan Panggung.
  2. Hermes hanya **membaca** (MCP read-only) dan harus menyebut sumber jawaban.
  3. Manusia (Ashar) yang memutuskan data terpercaya. Tidak ada auto-trust.
- File acuan perilaku: `panggung-prototipe-acuan.html`. Baca fungsi `analyze`, `checksFor`, `buildClean`, `previewHtml`, `applyDomain`, `answer`, dan CSS-nya. **Port aturannya ke Python dengan tes**, dan tiru tampilannya. Jangan menyalin bagian simulasi: `seed()`, `sim()`, state `D`/`P`, dan pembangkit data di `genSales`/`sampleSet`/`dirty` (pembangkit file contoh boleh dipindah ke `scripts/` untuk seeding demo).
- Nama kolom per channel di prototipe (`ALIAS`) hanyalah **ilustrasi**. Jangan klaim itu format ekspor asli TikTok Shop/Shopee/Lazada. Simpan sebagai konfigurasi yang mudah diganti, dan beri catatan "ilustrasi, ganti dengan ekspor asli".

## 1. Aturan kerja (berlaku untuk semua milestone)

1. Kerjakan **satu milestone per branch** (`feat/stage-m1-...`, dst). **Jangan merge ke main** sebelum Ashar menyetujui. Berhenti di akhir tiap milestone dan lapor.
2. Jangan menyentuh branch `wip-row-decisions`, dan jangan menyentuh tabel `kompas_*`.
3. Perubahan skema lewat migrasi Alembic dengan `downgrade` yang berfungsi. Migrasi tidak boleh membuat data (seed lewat skrip terpisah).
4. Setiap perubahan perilaku harus ada tes pytest. Jalankan seluruh suite sebelum lapor; laporkan jumlah tes lulus/gagal.
5. Jangan menampilkan, mencetak, atau mengutip isi `.env`, API key, atau connection string, di log, tes, fixture, maupun respons.
6. Operasi yang menghapus data (reset demo) hanya boleh menyentuh bisnis dengan `is_demo = true`, dan harus menampilkan jumlah yang akan dihapus lebih dulu sebelum menjalankan.
7. Jika menemukan hal yang bertentangan dengan dokumen ini, **tanya Ashar**, jangan menebak.
8. Pakai komponen dan gaya yang sudah ada di dashboard bila cocok. Jangan membuat sistem desain baru.
9. Untuk tes yang butuh MinIO, nyalakan dulu container tes (`docker start talatee-minio-test`, port 9100).

## 2. Milestone

### M0: Pemeriksaan (tanpa kode)
Periksa repo, lalu laporkan (ringkas, bukan salinan kode):
- Bagaimana bisnis, dataset, batch, file, dan baris transaksi tersimpan sekarang. Apakah sudah ada tabel baris transaksi yang ternormalisasi? Bagaimana format `talateeshop-*.csv` diproses?
- Di mana status kepercayaan diatur, dan bagaimana `process_dataset` menentukan statusnya.
- Cara autentikasi/otorisasi yang ada (API key per bisnis, login pemilik), dan apakah API key terikat ke satu bisnis.
- Isi `scripts/demo_simulator.py`, `app/mcp/server.py` (tool apa saja), dan `app/api/routes/chat.py`.
- `dashboard/src/` : struktur routing, `Stage.jsx`, `ShowcaseControl.jsx`, komponen Upload Data dan Data Explorer yang bisa dipakai ulang.
- Usulan konkret untuk: (a) kolom `is_demo`, (b) cara menandai dataset "ditahan otomatis" beserta alasannya, (c) cara menandai dataset "digantikan oleh versi bersih" **tanpa mengubah enum status** (usul: kolom nullable `superseded_by_dataset_id`), (d) tabel kanonik per domain (lihat M2), (e) di mana aturan kualitas diletakkan di pipeline ingestion.
- Daftar risiko dan hal yang tidak jelas.

**Selesai bila:** laporan diterima Ashar. Belum ada perubahan kode.

### M1: Fondasi demo
- Migrasi `businesses.is_demo BOOLEAN NOT NULL DEFAULT FALSE`; model diperbarui.
- Skrip `scripts/seed_demo.py` (idempoten): membuat bisnis "Talatee Skincare" dengan `is_demo = true` bila belum ada, plus satu API key demo yang terikat ke bisnis itu.
- `scripts/demo_simulator.py`: ganti guard `'demo' in nama.lower()` dengan pengecekan `is_demo`.
- **Reset demo** (service + endpoint pemilik + tombol di halaman Showcase): menghapus dataset, batch, file, dan objek MinIO milik bisnis demo saja. Tampilkan pratinjau jumlah, minta konfirmasi, lalu jalankan. Tidak menyentuh bisnis non-demo.
- Tombol **Simulator data** di Showcase memanggil simulator (mengirim transaksi lewat jalur upload yang sama dengan upload manual).
- Tes: reset tidak pernah menyentuh bisnis non-demo; simulator menolak bisnis non-demo; seed idempoten.

**Selesai bila:** Ashar bisa menekan Simulator dan Reset di Showcase, dan data demo bertambah/hilang tanpa menyentuh bisnis lain.

### M2: Domain data + aturan kualitas di ingestion
Aturan **hidup di backend ingestion**, berlaku sama untuk upload manual, simulator, dan (nanti) API.

**Adapter header:** peta alias nama kolom → nama baku (dari `ALIAS` prototipe) sebagai file konfigurasi, dipakai sebelum validasi. Simpan daftar pemetaan yang terjadi di ringkasan batch ("N kolom dipetakan").

**Deteksi domain** dari header setelah pemetaan:
- Penjualan: `transaction_ref, produk, kategori, qty, subtotal`
- Stok: `produk, stok`
- Marketing: `kampanye, biaya`
- Katalog: `sku, produk, harga_satuan`
- selain itu: "Data lain" (tidak masuk Panggung)

**Tabel kanonik** (usulan; sesuaikan dengan hasil M0, utamakan memakai ulang struktur yang ada). Semua baris membawa `dataset_id` sehingga gerbang `TRUSTED` berlaku lewat join:
- penjualan: `order_ref, order_date, channel, product_name, sku?, category, qty, unit_price, subtotal, status?`
- stok (snapshot): `sku?, product_name, stock, batch_code?, expiry_date?`
- marketing harian: `date, channel, campaign, spend, impressions, clicks, orders, revenue`
- katalog: `sku, product_name, category, price`

**Aturan kualitas** (lihat bagian 3 untuk rincian). Hasil tiap file disimpan: jumlah baris, jumlah lolos, alasan penolakan per jenis, daftar baris bermasalah beserta alasan, perbaikan otomatis yang dilakukan, dan persentase lolos.

**Penahanan otomatis:** bila persentase lolos < 70%, dataset otomatis berstatus `NEEDS_REVIEW` dengan alasan "ditahan otomatis", dan **tidak bisa** dipromosikan ke `TRUSTED` (tolak di service, bukan hanya di UI). File dengan isi persis sama (hash SHA-256 per bisnis) otomatis `NEEDS_REVIEW` dengan alasan "duplikat dari <dataset>".

**Selesai bila:** tes pytest untuk setiap aturan lulus (lihat daftar tes di bagian 3), dan seluruh suite lama tetap hijau.

### M3: Pembersihan data (cleaning)
Service + endpoint pemilik. Dua langkah: **pratinjau** lalu **terapkan**.
- Otomatis dirapikan: huruf kategori ke nama baku, format angka (`Rp 50.000` → `50000`), format tanggal ke ISO, spasi.
- Otomatis dibuang: baris ganda, pesanan batal/retur, dan baris yang tidak bisa diperbaiki (tanggal/qty/nilai tidak valid, nilai ekstrem).
- Opsional (default mati, harus dicentang): hitung ulang `subtotal = qty × harga_satuan`. Pratinjau wajib menyebut bahwa ini mengandalkan asumsi qty dan harga benar, dan hasilnya dicatat di dataset hasil.
- **Tidak ada nilai yang dikarang.** Selain perhitungan opsional di atas, tidak boleh ada imputasi.
- Pratinjau mengembalikan: jumlah nilai dirapikan per kolom, contoh perubahan (sebelum → sesudah), daftar baris yang dibuang beserta alasannya, dan "N dari M baris layak berhasil diselamatkan (X%)". Baris ganda dan batal/retur tidak dihitung sebagai kegagalan.
- Penerapan: **file asli tidak diubah.** Dibuat dataset baru bernama `<nama>-bersih` (file CSV baru di MinIO, melewati ingestion yang sama, status awal sama seperti upload biasa). Dataset asli ditandai digantikan (`superseded_by_dataset_id`), dikeluarkan dari hitungan, dan tidak bisa dipromosikan.
- Jika yang bisa diselamatkan < 70% baris layak, penerapan **ditolak** dengan pesan agar meminta file yang benar dari sumbernya.
- Pembersihan hanya untuk dataset Penjualan berstatus menunggu verifikasi atau ditahan. Dataset `TRUSTED` tidak boleh dibersihkan ulang (mencegah hitungan ganda).
- Dataset hasil tetap menunggu verifikasi manusia.

**Selesai bila:** tes lulus untuk: file asli tidak berubah, asli ditandai digantikan dan tidak bisa dipromosikan, hasil tidak menggandakan hitungan, penolakan di bawah 70%, opsi hitung ulang tercatat.

### M4: Halaman Gudang Data di Control Center
Halaman baru (mis. di bawah Showcase) hanya untuk pemilik. Acuan tampilan: laci "Gudang data" di prototipe.
- Upload **banyak file sekaligus** (seret & lepas atau pilih), hanya `.csv`, maks 3 MB per file untuk demo. Target upload selalu bisnis demo.
- Daftar semua file: nama, domain, channel, jumlah baris, persen lolos, ukuran, status (Baru masuk, Siap diverifikasi, Perlu ditinjau, Ditahan, Terpercaya, Digantikan). Filter folder: Semua / Penjualan / Stok / Marketing / Katalog dengan hitungan.
- Detail file: cuplikan baris (baris bermasalah ditampilkan lebih dulu, dengan kolom "Pemeriksaan" per baris), daftar hasil pemeriksaan, dan tombol **Tandai terpercaya** / **Perlu ditinjau** (tidak tersedia untuk file yang ditahan).
- Blok **Bersihkan data** (pratinjau → buat file bersih) sesuai M3.
- Tombol **Tandai semua terpercaya** (melewati yang ditahan, dan memberi tahu jumlahnya).
- Lencana jumlah file yang menunggu verifikasi/ditahan pada menu, dan notifikasi saat ada file ditahan.
- Tombol "isi contoh Talatee Skincare" (memakai generator di `scripts/`): 4 file penjualan (TikTok Shop, Shopee, Lazada, WhatsApp), stok, marketing, katalog; plus 2 file kotor untuk demonstrasi. Tombol dan skrip ini hanya bekerja untuk bisnis demo.
- Semua teks dari file ditampilkan sebagai teks (escape), bukan HTML.

**Selesai bila:** Ashar bisa mengunggah banyak file, melihat isinya, membersihkan, dan memverifikasi, lalu angka di Overview bisnis demo berubah hanya untuk data terpercaya.

### M5: Endpoint ringkasan publik + Panggung nyata
`GET /public/stage/summary` (rincian di bagian 4) dan penulisan ulang `Stage.jsx` mengikuti prototipe: kartu alur 5 tahap, KPI, tren 30 hari, produk terlaris (donat), bar status kepercayaan, omzet per channel, stok menipis, kampanye marketing, panel Hermes terakhir.
- Polling tiap 4 detik, berhenti saat tab tidak terlihat. Tombol **Mode siaran** (huruf besar, panel log disembunyikan).
- **Tanpa kotak chat bebas untuk publik** (risiko biaya dan prompt injection). Panel Hermes menampilkan pertanyaan, tool yang dipanggil, jawaban, dan sumber terakhir dari log (M6). Pertanyaan diajukan Ashar dari halaman Hermes di Control Center.
- Panel yang belum punya data menampilkan "Belum tersambung" / "Belum ada data terpercaya", bukan angka palsu.
- Tidak ada kata terlarang (bagian 0) di HTML, judul tab, atau respons API. Judul tab: "Talatee Skincare · Panggung".

**Selesai bila:** tes backend (isolasi demo, keamanan) lulus, dan Panggung terisi dari data demo terpercaya yang diunggah lewat Gudang.

### M6: Log Hermes + tool MCP domain baru
- Tabel `hermes_interactions`: `id, business_id, asked_at, question, tools_called (json), answer, sources (json), is_demo`. Hanya mencatat interaksi yang konteksnya bisnis demo. Pertanyaan/jawaban disanitasi sebelum disimpan untuk Panggung (hapus pola secret/URL berkredensial, potong 300 karakter).
- Tool MCP baru (read-only, hanya data `TRUSTED`, terikat ke bisnis): `cek_stok` (sisa hari = stok ÷ rata-rata penjualan harian 30 hari; batch kedaluwarsa tidak dihitung tersedia), `ringkas_kampanye` (ROAS = omzet ÷ biaya), `ringkas_per_channel`. Jawaban tool harus memuat label sumber (dataset/batch).
- Kartu "Log Hermes" di Showcase menampilkan log lengkap untuk pemilik.

**Selesai bila:** kalimat "hasilnya dicatat di sistem" benar-benar benar, dan Hermes menjawab pertanyaan stok, kampanye, dan channel dari data terpercaya dengan sumber.

## 3. Aturan kualitas data (spesifikasi)

Konstanta (jadikan konfigurasi per bisnis dengan nilai awal ini): `PASS_THRESHOLD = 0.70`, `OUTLIER_MAX_SUBTOTAL = 5_000_000`, `MISMATCH_TOLERANCE = 1` (rupiah).

**Persen lolos** = baris lolos ÷ (total baris − baris batal/retur). Bila penyebut 0, nilainya 1. Baris ganda tetap dihitung sebagai kegagalan di file asli.

**Penjualan** (urutan pemeriksaan; alasan pertama yang gagal yang dicatat):
1. Ganda: kunci `(order_ref, produk)` sudah muncul di file yang sama atau di data valid milik bisnis yang sama.
2. Tanggal: harus terbaca (format `YYYY-MM-DD` atau `DD/MM/YYYY`, tanggal yang benar-benar ada). Tanggal **masa depan ditolak**. Tanggal lama **diterima** (berbeda dari prototipe, yang hanya menolak karena grafiknya 30 hari; grafik di Panggung tetap menampilkan 30 hari terakhir).
3. Status batal/retur (`batal, dibatalkan, cancel, cancelled, canceled, retur, return, returned, refund, gagal`, tidak peka huruf besar-kecil) hanya bila kolom status ada. Tidak dihitung dan tidak dianggap kegagalan.
4. `qty` bilangan bulat ≥ 1.
5. `subtotal` angka ≥ 0 (format `Rp 50.000` dan `50.000,5` dibaca ulang).
6. `subtotal` > `OUTLIER_MAX_SUBTOTAL` → nilai tidak masuk akal.
7. Bila `harga_satuan` ada dan terbaca: `|qty × harga_satuan − subtotal| ≤ MISMATCH_TOLERANCE`, jika tidak → subtotal tidak cocok.
- Perbaikan otomatis yang dicatat (bukan penolakan): huruf kategori dirapikan ke nama baku, kategori tidak dikenal masuk "Lainnya" (dilaporkan), format angka dibaca ulang, produk yang tidak ada di katalog SKU ditandai peringatan (bukan penolakan, hanya bila katalog terpercaya sudah ada).
- Catatan: tanpa kolom `tanggal`, baris dihitung sebagai hari ini (dilaporkan). Tanpa kolom `status`, pesanan batal tidak bisa disaring (dilaporkan).
- Channel: dari kolom `channel` per baris, bila tidak ada dari kata kunci nama file (`tiktok`, `shopee`, `lazada`, `whatsapp`/`wa`, `web`), selain itu "Lainnya".

**Stok:** SKU/produk tidak ganda dalam file; `stok` bilangan bulat ≥ 0; `kedaluwarsa` (bila ada) harus tanggal valid, dan batch yang sudah lewat tanggal dihitung peringatan (disimpan, tetapi tidak dihitung sebagai stok tersedia). Snapshot: nilai terakhir yang terpercaya per SKU menggantikan yang lama.

**Marketing:** tanggal valid dan tidak di masa depan; `biaya ≥ 0`; `tayangan, klik, order, omzet` ≥ 0 dan `order ≤ klik ≤ tayangan`; kunci ganda `(tanggal, kampanye, channel)`. Agregasi per `(kampanye, channel)`: ROAS = omzet ÷ biaya.

**Katalog:** SKU wajib, unik dalam file; `harga_satuan > 0`.

**Tes minimal (pytest)** untuk: setiap alasan penolakan; format angka Indonesia; tanggal tidak ada (31/02); penahanan di bawah 70%; promosi ke TRUSTED ditolak untuk dataset ditahan; file kembar; baris ganda lintas file tidak menggandakan hitungan; pesanan batal tidak dihitung; batal/retur tidak menurunkan persen lolos; adapter header; deteksi domain; stok kedaluwarsa tidak dihitung tersedia; funnel marketing tidak masuk akal; SKU ganda dan harga nol di katalog; reset hanya bisnis demo; endpoint ringkasan tidak membocorkan data bisnis non-demo.

## 4. Spesifikasi `GET /public/stage/summary`

- Tanpa login, **hanya GET**, **hanya SELECT**, hanya data bisnis `is_demo = true` dan dataset `TRUSTED` (kecuali hitungan alur/status). Filter demo ada di **level query/repository**, bukan hanya di frontend. Pakai role/koneksi database read-only bila memungkinkan.
- Rate limit ringan (mis. 30 req/menit per IP), `Cache-Control: s-maxage=3..5`. Error → 503 dengan pesan generik. Catat di dokumentasi bahwa rate limit in-memory tidak andal pada banyak instance.
- Respons tidak boleh memuat: API key, token, URL internal, path MinIO, connection string, ID bisnis non-demo, stack trace, **nama file asli**. Teks Hermes disanitasi (hapus pola secret, potong 300 karakter, tanpa nama tool/tabel yang mengandung "talatee" atau "kompas").
- Peristiwa untuk Panggung dibuat generik ("1 file ditahan"), tanpa nama file.

Bentuk respons (nilai contoh):

```json
{
  "generated_at": "2026-10-12T03:00:00Z",
  "brand": "Talatee Skincare",
  "demo_active": true,
  "flow": {
    "file_masuk":      {"count": 7, "last_event_at": "..."},
    "batch_tercatat":  {"count": 7, "last_event_at": "..."},
    "terpercaya":      {"count": 5, "last_event_at": "..."},
    "hermes_bertanya": {"count": 0, "last_event_at": null},
    "jawaban_sumber":  {"count": 0, "last_event_at": null}
  },
  "trust": {"ingested": 0, "validating": 1, "needs_review": 1, "trusted": 5, "held": 1},
  "kpi": {"omzet_30d": 0, "order_30d": 0, "omzet_7d": 0, "omzet_7d_prev": 0, "batch_lolos_pct": 100},
  "daily": [{"date": "2026-09-13", "revenue": 0, "orders": 0}],
  "categories": [{"name": "Skincare", "revenue": 0}],
  "channels": [{"name": "TikTok Shop", "revenue": 0}],
  "stock": [{"product": "Serum Vitamin C", "stock": 40, "days_cover": 3.9, "expired": false}],
  "campaigns": [{"campaign": "Serum Flash Sale", "channel": "TikTok Shop", "spend": 0, "revenue": 0, "roas": 6.3}],
  "hermes_last": {"question": "...", "tools": ["cek_stok"], "answer": "...", "sources": [{"dataset_label": "...", "batch_label": "..."}], "at": "..."},
  "events": [{"at": "...", "text": "1 file ditahan", "tone": "warn"}]
}
```

- `daily` selalu 30 entri (hari tanpa data bernilai 0). `stock` maksimal 5 SKU dengan sisa hari terendah. Bila sumber data belum ada, kembalikan hitungan 0/array kosong/`null`, jangan error.

## 5. Keamanan (wajib)

1. Semua endpoint Gudang/Reset/Simulator hanya untuk pemilik (autentikasi yang sudah ada), dan target upload dipaksa ke bisnis demo di sisi server.
2. API key demo terikat ke satu bisnis demo; tidak ada jalur yang memungkinkan upload ke bisnis non-demo lewat fitur ini.
3. Validasi upload: hanya CSV, maks 3 MB per file, batas jumlah baris (usul 50.000), tolak byte NULL, jangan memproses `.xlsx`/biner.
4. Tidak ada endpoint publik yang menulis data, mengunggah file, atau memanggil LLM.
5. Jika nanti ada fitur ekspor/unduh CSV, awali sel yang diawali `= + - @` dengan tanda kutip tunggal (mencegah formula injection).
6. Panggung dan Control Center sebaiknya di domain berbeda. Itu bagian terpisah di luar milestone ini (middleware host), jangan dikerjakan sekarang.

## 6. Di luar cakupan Tahap 1

- Koneksi API langsung ke marketplace (Tahap 2: backend yang memanggil API, kunci disimpan terenkripsi di server, tidak pernah ke browser).
- Kotak chat Hermes terbuka untuk publik.
- Domain kedua untuk Panggung dan middleware host.
- Integrasi WhatsApp/n8n.

## 7. Format laporan di akhir setiap milestone

1. Apa yang dibuat/diubah (daftar file), singkat.
2. Hasil `pytest`: jumlah lulus/gagal.
3. Cara Ashar memeriksa secara manual (langkah klik, bukan perintah teknis).
4. Hal yang belum selesai, risiko, dan pertanyaan.
5. Nama branch, dan **jangan merge** sampai disetujui.
