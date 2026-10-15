# PANGGUNG: Piagam dan Aturan

> Dokumen hidup. Bagian bertanda **[TETAP]** tidak diubah tanpa catatan keputusan tertulis (lihat Bagian 10).
> Bagian lain boleh berkembang. Setiap perubahan dicatat di Bagian 12.
>
> **Versi 1.1 · 15 Oktober 2026 · Pemilik: Ashar (Talatee)**

---

## 0. Cara memakai dokumen ini

- **Sebelum mengubah apa pun di Panggung**, baca Bagian 2 (prinsip), 3 (kontrak), dan 6 (aturan perubahan).
- **Sebelum live**, jalankan daftar periksa di Bagian 11.
- **Saat memakai asisten AI**, tempel atau tunjuk dokumen ini di awal sesi, dan ikuti Bagian 7.
- Letak yang disarankan: `docs/PANGGUNG.md` di repo, dan ditautkan dari README.

---

## 1. Apa itu Panggung

Panggung (`/stage`) adalah layar tontonan untuk konten dan siaran langsung. Layar ini memperlihatkan bagaimana data mengalir dari file masuk, tercatat, divalidasi, sampai menjadi angka yang bisa dipercaya, dan nantinya dijawab oleh agen AI dengan sumbernya.

**Yang membuatnya berbeda:** semua yang tampil adalah kejadian nyata dari database. Tidak ada angka, animasi, atau jawaban yang dikarang.

**Bukan tujuan Panggung:**
- Menampilkan data klien sungguhan.
- Menjadi dasbor operasional harian (itu tugas dashboard utama).
- Mengubah aturan kepercayaan data di inti sistem.

---

## 2. Prinsip inti **[TETAP]**

| # | Prinsip | Alasan |
|---|---|---|
| P1 | **Hanya bisnis demo.** Panggung hanya membaca dan menulis bisnis bertanda `is_demo`. Setiap endpoint Panggung memeriksa ini di server, bukan di tampilan. | Layar ini disiarkan. Satu kebocoran data klien merusak kepercayaan. |
| P2 | **Angka uang hanya dari data TRUSTED.** Satu-satunya jalan ke TRUSTED adalah `promote_dataset`. Panggung tidak boleh membuat jalan pintas. | Menjaga janji "angka ini sudah disetujui". |
| P3 | **Unggahan manual menunggu persetujuan.** Bawaannya `promote=false`. Melewati persetujuan harus pilihan sadar yang terlihat. | Persetujuan adalah momen cerita sekaligus penjaga mutu. |
| P4 | **Jujur di layar.** Label harus mencerminkan keadaan sebenarnya. Tag "Data demo" dan catatan kaki tidak dihapus. Simulasi selalu berlabel simulasi. | Penonton menilai kejujuran lebih tajam daripada visual. |
| P5 | **Gerak = kejadian nyata.** Animasi dipicu cap waktu `flow.*.last`, `agent.step`, atau aksi pengguna. Timer hanya boleh untuk ambience yang tidak mengklaim apa-apa (garis putus-putus yang bergerak). | Mencegah layar "berpura-pura sibuk". |
| P6 | **Tidak ada jawaban atau insight karangan.** Node Hermes tetap redup bertuliskan "Belum tersambung" sampai ada log nyata. Insight hanya dari sumber yang ada. | Reputasi. |
| P7 | **Rahasia tidak pernah tampil.** Kunci API ditampilkan sekali saat dibuat, tidak ada tombol "tampilkan", dan awalan kunci disembunyikan saat mode siaran. Tidak ada galat mentah di layar. | Layar bisa direkam dan dipotret. |
| P8 | **Data mentah tidak diubah.** Gudang Data menampilkan isi file persis seperti masuk. Pembersihan menghasilkan salinan. | Bukti bahwa sistem tidak mengubah data diam-diam. |
| P9 | **Satu tahap = satu commit = bisa dibatalkan.** Perubahan besar dipecah supaya `git restore` atau revert tetap mudah. | Panggung dipakai live, jadi pemulihan harus cepat. |
| P10 | **Tes tidak menyentuh database utama.** Tes memakai `talatee_test` (port 5434). Perintah yang mengubah database utama (misalnya `seed_demo.py`) dijalankan sadar dan tanpa `--adopt` pada bisnis klien. | Database utama berisi data sungguhan. |

---

## 3. Batas arsitektur dan kontrak **[TETAP]**

### 3.1 Peta berkas

**Backend**

| Berkas | Tugas |
|---|---|
| `app/api/routes/stage.py` | `/stage/summary`, `/stage/batches/{id}`, `/stage/batches/{id}/promote` |
| `app/schemas/stage.py` | Bentuk respons (kontrak) |
| `app/services/stage_activity.py` | Menurunkan `events` dan `agent` dari status database (fungsi murni) |
| `app/services/stage_batches.py` | Memetakan status batch ke status tampilan (fungsi murni) |
| `app/api/routes/showcase_control.py` | `/showcase/*`: simulator, unggah demo, isi 30 hari, reset (hanya demo) |
| `scripts/seed_demo.py` | Membuat bisnis "Skincare Demo" dan kunci API-nya |

**Frontend** (`dashboard/src/pages/`)

| Berkas | Tugas |
|---|---|
| `Stage.jsx` | Susunan halaman, pintasan, mode siaran |
| `PipeCanvas.jsx` | Kanvas alur data (lima node) |
| `StageIntake.jsx` | Laci "Tambah data": unggah, persetujuan, status API |
| `StageGudang.jsx` / `StageBersih.jsx` / `StageAgent.jsx` / `StageControls.jsx` | Halaman dan panel |
| `useStageData.js` | Sumber data (mode `api` atau `mock`) |
| `useBatchDetail.js` | Isi mentah dan laporan masalah satu batch |
| `stage.css` | Semua gaya Panggung (memakai variabel tema: `--g`, `--line`, `--panel`, `--bg`, `--tx`, `--mut`) |

### 3.2 Kontrak `/stage/summary`

Aturan: **hanya boleh menambah field.** Tidak boleh mengganti nama atau menghapus tanpa catatan keputusan. Tampilan harus toleran terhadap field yang belum ada.

```
flow:     { file, batch, trust{INGESTED,VALIDATING,NEEDS_REVIEW,TRUSTED,last}, question, answer }  (last = epoch ms)
trend, categories, channels, low_stock, hermes, feed, hermes_connected
events:   [{ t, kind, text, tone, batchId }]
agent:    { status: idle|working, step: read|clean|validate|trust|insight|null, batchId, label, lastDone }
batches:  [{ id, file, channel, rows, status, trust, t, cols, raw, clean, stats }]
api:      { configured, key_prefix, last_used }
```

### 3.3 Endpoint

| Endpoint | Perlindungan |
|---|---|
| `GET /stage/summary` | Sesi dashboard; hanya demo |
| `GET /stage/batches/{id}` | Sesi dashboard; batch non-demo dijawab 404 |
| `POST /stage/batches/{id}/promote` | Sesi dashboard; hanya demo; lewat `promote_dataset`; galat dijawab umum (409) |
| `POST /showcase/demo/upload` | Hanya demo; batas 5 MB; hanya `.csv` dan `.xlsx` |
| `POST /showcase/reset` | Perlu `confirm=true`; hanya bisnis demo |

### 3.4 Mode dan pintasan

- Mode data: `VITE_STAGE_MODE=api` (database) atau `mock` (simulasi di browser, berlabel). `?mock` memaksa simulasi.
- Bendera URL: `?siaran` `?potret` `?lanskap` `?otomatis` `?ikuti`.
- Pintasan: `1`/`2` halaman · `F` agen memandu · `B` mode siaran · `V` orientasi · `C` kendali demo · `U` tambah data · `P` jeda simulasi · `Esc` menutup.

---

## 4. Aturan data dan kepercayaan **[TETAP]**

**Status kepercayaan** berasal dari tabel `datasets.trust_status`:
`INGESTED → VALIDATING → TRUSTED`, atau `NEEDS_REVIEW` bila validasi menemukan error (termasuk skor kualitas di bawah 70 dan subtotal yang tidak cocok dengan qty × harga).

**Pemetaan ke tampilan:**

| Kondisi nyata | Label tampilan | Catatan |
|---|---|---|
| batch `running` | Diproses | |
| `INGESTED` baru berubah (≤45 dtk) | Diproses | |
| `VALIDATING` baru berubah (≤45 dtk) | Diproses | |
| `VALIDATING` lama | **Siap diverifikasi** | Sejak v1.1. |
| `NEEDS_REVIEW` atau batch `failed` | Perlu ditinjau | Tidak dihitung ke omzet |
| `TRUSTED` | Terpercaya | Satu-satunya yang dihitung ke omzet |

**Aturan unggahan Panggung:** satu file = satu dataset (`Upload <nama file> <jam>`). Persetujuan berlaku per file. Konsekuensinya: dua file berisi order yang sama terhitung dua kali (lihat Keputusan D-003).

---

## 5. Aturan layar siaran dan live **[TETAP]**

1. Mode siaran (`B`) menyembunyikan tombol kendali dan awalan kunci API.
2. Layar potret dan jendela sempit memakai deretan kartu lama, bukan kanvas, karena teks kanvas terlalu kecil.
3. Seret-file ke layar tetap bekerja saat siaran. Hasilnya tampil sebagai notifikasi singkat.
4. Pesan galat di layar hanya pesan 4xx yang sudah dikurasi backend. Detail teknis hanya di konsol.
5. Tab Panggung yang tersembunyi tidak ikut memanggil backend. Tutup tab Panggung yang tidak dipakai (tiap tab memanggil backend tiap 3 detik).
6. Judul tab dan ikon diganti selama Panggung terbuka. `index.html` masih bertuliskan "Talatee" sampai React jalan, jadi buka halaman ini **sebelum** mulai berbagi layar.

---

## 6. Aturan perubahan

### 6.1 Boleh berubah bebas
Teks, warna, ukuran, animasi (selama P4 dan P5 terjaga), tata letak panel, urutan pintasan, tes tambahan, perbaikan galat.

### 6.2 Perlu catatan keputusan dan persetujuan pemilik
Segala hal yang menyentuh P1 sampai P10, kontrak di Bagian 3, aturan kepercayaan (Bagian 4), serta penghapusan atau penggantian nama field.

### 6.3 Dilarang
- Menambah jalan pintas ke TRUSTED di luar `promote_dataset`.
- Membaca atau menulis bisnis non-demo dari endpoint Panggung.
- Menampilkan kunci API, kredensial, alamat internal, atau teks galat mentah.
- Menampilkan angka atau jawaban yang tidak berasal dari database.
- Menghapus tag "Data demo" atau catatan kaki.

### 6.4 Proses
1. Tulis rencana singkat, termasuk bagian mana yang disentuh.
2. Kerjakan kecil dan bisa dibatalkan (satu tahap, satu commit).
3. Jalankan tes dan lint (daftar periksa Bagian 11).
4. Lihat hasilnya di layar sebelum dianggap selesai.
5. Perbarui Bagian 8 (status) dan Bagian 12 (riwayat).

### 6.5 Definisi selesai
- `pytest` untuk `tests/test_stage_batches.py`, `tests/test_stage_summary.py`, `tests/test_showcase_control.py` lulus.
- `npm run lint` tanpa galat (peringatan lama boleh ada, peringatan baru dijelaskan).
- Fungsi murni baru punya tes.
- Diuji di layar, termasuk mode siaran.
- Tidak ada rahasia di diff.

---

## 7. Aturan untuk asisten AI dan kontributor

1. Baca dokumen ini sebelum mengusulkan perubahan.
2. Jangan menyentuh Bagian 2, 3, dan 4 tanpa membuat usulan keputusan dan menunggu persetujuan eksplisit.
3. Jangan menambah fitur di luar fase yang sedang berjalan (Bagian 9) tanpa bertanya.
4. Kerjakan dalam tahap kecil yang bisa dikembalikan. Sebelum mengubah file, pastikan ada commit sebelumnya.
5. Jangan mencetak atau menyarankan menempel kunci API, kata sandi, atau isi `.env`.
6. Jangan menjalankan perintah yang mengubah database utama tanpa menyebut dengan jelas apa yang berubah.
7. Pakai variabel tema yang ada. Jangan mengubah gaya halaman lain.
8. Perhatikan akhir baris file Windows (CRLF). Skrip penambal harus mempertahankannya.
9. Kalau sebuah klaim tentang kode belum dilihat langsung, katakan itu belum terverifikasi.
10. Bahasa antarmuka: Indonesia, ringkas, dan sesuai keadaan sebenarnya.

---

## 8. Status saat ini (15 Oktober 2026)

### Sudah berjalan
- Kanvas alur data lima node, digerakkan peristiwa nyata (cahaya di kurva, kedipan "+1", node menyala saat agen bekerja).
- `/stage/summary` mengirim `events`, `agent`, `batches`, dan `api`.
- Gudang Data: daftar kedatangan nyata dan tabel data mentah dari database, lengkap dengan tanda sel kosong, format berbeda, dan duplikat.
- Laci "Tambah data": unggah manual (pilih file, atau seret ke mana saja), antrean persetujuan dengan "Tandai terpercaya", status koneksi API.
- Endpoint detail dan promote khusus bisnis demo.
- Bisnis demo "Skincare Demo" dan kunci API terikat sudah ada di database.
- Pemeriksa kualitas baris menerima kolom jam dan tanggal-jam gabungan; versi bersih tidak lagi mengarantina semua baris pada file seperti itu.
- Reset demo ikut membersihkan entri Laboratorium milik bisnis demo.
- Tes: 9 lulus (tes baru ikut terhitung). Lint: 0 galat.

### Belum ada
- Log Hermes (pertanyaan, tool, sumber, jawaban) dan chat. Node Hermes redup.
- Insight dari agen (halaman Data Bersih masih kosong sampai data TRUSTED ada dan sumber insight dibuat).
- Pembuatan kunci API dari layar, dan alamat endpoint terima data.
- Stok, marketing, dan katalog.
- Pengambilan data otomatis dari marketplace atau Google Sheets.
- Pelindung duplikat antar file.

### Masalah yang diketahui
1. ~~Label "Bersih" untuk file yang belum disetujui.~~ **Selesai (v1.1):** status `VALIDATING` lama kini tampil "Siap diverifikasi".
2. ~~Kolom `waktu` ditandai "format berbeda" di semua baris.~~ **Selesai (v1.1):** `waktu` termasuk petunjuk kolom tanggal, sehingga nilai jam (`09:18`) dianggap tanggal salah dan seluruh baris masuk karantina. `issue_checks.py` kini menerima jam pada kolom waktu/jam, dan tanggal-jam gabungan.
3. **Database ada di Neon (cloud).** Respons Postgres tercatat 1,1 sampai 1,7 detik di Showcase. Ringkasan Panggung menjalankan beberapa query tiap 3 detik, jadi animasi bisa terlambat muncul.
4. **Server Hermes berstatus Mati** di Showcase.
5. Tabel Data mentah hanya memuat 40 baris pertama.
6. Kunci API demo sempat tampil di chat. Putar ulang satu kali menjelang live pertama (`python scripts\seed_demo.py --new-key`), lalu simpan tanpa menyalin ke mana pun.
7. Peringatan lint lama (sekitar 24, 0 galat) berasal dari pola `setState` di dalam effect dan ekspor non-komponen.

---

## 9. Peta jalan

Setiap fase punya gerbang. Fase berikutnya baru dimulai bila gerbangnya terpenuhi.

### Fase 0: Mantapkan sebelum live
- [x] Label "Siap diverifikasi" menggantikan "Bersih".
- [x] Sebab kolom `waktu` ditandai diperiksa dan diperbaiki.
- [ ] Cache ringkasan singkat di server dan perlambat polling saat tidak ada aktivitas (bila respons masih di atas 1 detik).
- Latihan penuh: reset → isi data → unggah → setujui → omzet bergerak.
- **Gerbang:** satu latihan live tanpa kejutan, direkam, dan lolos daftar periksa Bagian 11.

### Fase 1: Hermes sungguhan
- Tabel log (pertanyaan, tool yang dipanggil, sumber, jawaban, waktu) dan endpoint.
- Server Hermes aktif; node "Hermes bertanya" dan "Jawaban + sumbernya" hidup dari log nyata.
- Panel tanya-jawab. Jawaban hanya dari data TRUSTED lewat MCP.
- **Gerbang:** satu pertanyaan live dijawab dengan nama tool dan sumbernya tercatat di database.

### Fase 2: Insight
- Insight berbasis aturan lebih dulu (produk terlaris, channel teratas, duplikat yang dicegah), lengkap dengan datanya.
- Insight oleh model hanya setelah aturan stabil, dan selalu menyebut sumber.
- **Gerbang:** tiap insight bisa ditelusuri ke batch dan angka asalnya.

### Fase 3: Domain lain
- Stok, marketing, katalog, masing-masing dengan aturan kepercayaan sendiri.
- **Gerbang:** tiap domain punya tes, tabel, dan pemeriksa kualitas sebelum tampil.

### Fase 4: Koneksi
- Tombol "Buat kunci baru" (kunci tampil sekali), dan dokumentasi endpoint terima data.
- Setelah itu, pengambilan data otomatis. Mulai dari yang paling sederhana (Google Sheets), baru marketplace.
- **Gerbang:** satu sistem luar (misalnya n8n) berhasil mengirim data dan terlihat di Panggung.

### Fase 5: Alat konten
- Rekam dan putar ulang jalannya data (skenario yang bisa diulang).
- Preset adegan (kosong, terisi, pembuka, penutup).
- **Gerbang:** satu konten dibuat sepenuhnya dari alat ini.

---

## 10. Catatan keputusan

Format: **ID · tanggal · keputusan · alasan · konsekuensi.** Keputusan baru ditambahkan di bawah. Keputusan lama tidak dihapus, hanya ditandai "diganti oleh".

- **D-001 · 15 Okt 2026 · Panggung hanya membaca bisnis demo.** Alasan: layar disiarkan. Konsekuensi: endpoint baru wajib memeriksa `is_demo`.
- **D-002 · 15 Okt 2026 · Unggahan manual bawaannya menunggu persetujuan.** Alasan: momen cerita dan penjaga mutu. Konsekuensi: ada kotak centang sadar untuk melewatinya.
- **D-003 · 15 Okt 2026 · Satu unggahan = satu dataset (pilihan A).** Alasan: persetujuan per file. Konsekuensi: file yang sama diunggah dua kali terhitung dua kali, perlu pelindung duplikat (Fase 0 atau 1). Bisa dikembalikan dengan satu baris di `showcase_control.py`.
- **D-004 · 15 Okt 2026 · "Tambah data" berupa laci mengambang.** Alasan: tidak mengubah tata letak halaman yang sudah disukai.
- **D-005 · 15 Okt 2026 · Batas skor kualitas 70 tetap di inti (`core.py`), bukan di Panggung.** Alasan: aturan teruji dan dipakai di luar Panggung.
- **D-006 · 15 Okt 2026 · Gerak dipicu data nyata, bukan timer.** Lihat P5.
- **D-007 · 15 Okt 2026 · Kunci API tampil sekali, tanpa tombol "tampilkan".** Alasan: kunci disimpan sebagai hash. Konsekuensi: lupa berarti buat baru.
- **D-008 · 15 Okt 2026 · "Sambungkan API" berarti menerima data dahulu.** Menarik data dari marketplace ditunda ke Fase 4.

---

## 11. Daftar periksa

### Sebelum live
- [ ] Docker menyala, Postgres dan MinIO "Normal" di halaman Showcase. Respons di bawah 1 detik, atau cache sudah aktif.
- [ ] Backend (`uvicorn app.main:app --reload`) dan frontend (`npm run dev`) berjalan.
- [ ] Server Hermes aktif (bila node Hermes dipakai). Bila tidak, tampilkan apa adanya: "Belum tersambung".
- [ ] **Reset demo** untuk keadaan awal yang diinginkan, atau **Isi data 30 hari** untuk keadaan terisi.
- [ ] Kunci API demo diputar ulang dan tidak ada di layar atau riwayat terminal (`Clear-Host`).
- [ ] Hanya satu tab Panggung terbuka. Tab lain ditutup.
- [ ] Halaman Panggung dibuka **sebelum** mulai berbagi layar (judul tab "Panggung").
- [ ] Mode siaran (`B`) dicoba, dan awalan kunci tidak tampil di laci.
- [ ] Satu unggahan uji lolos: unggah → muncul di Kedatangan → setujui → omzet bergerak.
- [ ] Notifikasi, terminal, dan jendela lain yang berisi rahasia ditutup.

### Sebelum menggabungkan perubahan
- [ ] Commit sebelumnya ada (titik kembali).
- [ ] `python -m pytest tests/test_stage_batches.py tests/test_stage_summary.py tests/test_showcase_control.py -q` lulus (Docker menyala).
- [ ] `npm run lint` tanpa galat.
- [ ] Dilihat di layar, termasuk mode siaran dan layar sempit.
- [ ] Bagian 8 dan Bagian 12 diperbarui.
- [ ] Tidak ada rahasia di `git diff`.

---

## 12. Riwayat dokumen

| Versi | Tanggal | Perubahan |
|---|---|---|
| 1.0 | 15 Okt 2026 | Piagam pertama: prinsip, kontrak, status, peta jalan, keputusan D-001 sampai D-008. |
| 1.1 | 15 Okt 2026 | Label "Siap diverifikasi" dan perbaikan kolom jam (`issue_checks.py`) selesai; Bagian 4, 8, dan 9 diperbarui. |

---

## 13. Istilah

- **Bisnis demo:** bisnis bertanda `is_demo`, satu-satunya yang dilihat Panggung ("Skincare Demo").
- **TRUSTED:** dataset yang sudah lolos validasi dan disetujui lewat `promote_dataset`.
- **Batch:** satu kali unggahan (satu file).
- **Agen:** urutan langkah pemrosesan (Baca, Bersihkan, Validasi, Percaya, Insight) yang dibaca dari status database. Langkah-langkah ini dijalankan kode aturan, bukan model AI. Hermes (AI) hanya muncul pada tahap tanya-jawab.
- **Mode siaran:** tampilan kanvas tetap 16:9 atau 9:16 untuk live.
