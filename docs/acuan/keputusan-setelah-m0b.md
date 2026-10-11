# Keputusan setelah M0b

Berlaku bersama `prompt-agent-tahap-1.md` dan `revisi-setelah-m0.md`. **Bila bertentangan, file ini yang menang.**

## 1. Keputusan

1. **Opsi B untuk bisnis demo.** Satu upload = satu Dataset. `dataset_name` = nama file tanpa ekstensi; bila sudah ada, tambahkan akhiran `-2`, `-3`, dan seterusnya agar tetap satu upload satu dataset. Bisnis non-demo **tidak berubah**.
2. **Alur demo:** upload → proses otomatis (memanggil `process_dataset`, jalur yang sama dengan tombol "Bersihkan Data") → hasil kualitas tampil → promosi ke `TRUSTED` tetap **manual** lewat `promote_dataset`. Tidak ada auto-trust.
3. **Kategori:** jangan memaksa daftar baku global. Pertahankan perapian "ejaan terbanyak" yang sudah ada. Khusus bisnis demo, bila Katalog SKU terpercaya sudah ada, kategorinya dipakai sebagai daftar baku.
4. **Nilai ekstrem:** aturan hanya aktif bila ambang diatur per bisnis. Nilai awal: tidak aktif. Bisnis demo diatur 5.000.000.
5. **Berlaku untuk semua bisnis:** tanggal masa depan dan `qty` ≥ 1 menjadi penyebab Karantina; format `Rp` ditambahkan ke `_parse_decimal`.
6. **Dedup lintas dataset:** pengaturan per bisnis `cross_dataset_dedup`, nilai awal false, **aktif untuk bisnis demo**. Baris yang kuncinya sudah ada di dataset lain milik bisnis yang sama masuk Karantina dengan alasan "sudah ada di dataset lain" dan dihitung sebagai kegagalan. Ini mencegah hitungan ganda di Panggung karena dedup yang ada hanya per dataset.
7. **Hitung ulang subtotal (Correction massal) ditunda.** Bukan bagian M3 awal, supaya tidak ada perubahan berbasis asumsi. Pembersihan = perbaikan deterministik + Karantina + pratinjau dry-run.
8. **Efek samping `get_dataset_quality()`:** fungsi GET ini menulis status `VALIDATING`/`NEEDS_REVIEW`. Jangan diubah di M1. Di M2, laporkan dulu dampaknya, dan pastikan penahanan otomatis tidak bisa tertimpa olehnya.
9. **Tampilan default:** bisnis demo tidak muncul di Overview, daftar Clients, Data Explorer, dan antrean Eksperimen secara default. Beri parameter `include_demo` dan ruang khusus demo di Gudang. Tool MCP `list_businesses` **menyertakan** bisnis demo dengan penanda `is_demo`, agar Hermes bisa memilihnya secara eksplisit.

## 2. M1a: penanda demo dan pengikatan key (branch `feat/stage-m1a-demo-flag`)

- Migrasi `businesses.is_demo BOOLEAN NOT NULL DEFAULT FALSE`, dan `api_keys.business_id` (UUID nullable, FK ke `businesses.id`). Keduanya dengan `downgrade` yang berfungsi.
- Penegakan: upload dengan key yang `business_id`-nya terisi dipaksa ke bisnis itu; `business_name` dari klien yang berbeda ditolak. Key tanpa `business_id` berperilaku seperti sekarang.
- `scripts/seed_demo.py` (idempoten): membuat bisnis "Talatee Skincare" dengan `is_demo = true`, plus satu API key demo terikat ke bisnis itu (tampilkan key **sekali** di terminal, jangan disimpan di log atau repo). Opsi `--adopt "Warung Demo"`: tampilkan apa yang akan ditandai dan minta konfirmasi sebelum menandainya `is_demo`.
- Penerapan butir 9 (filter default, `include_demo`, lencana "Demo" di Clients, `list_businesses` MCP).
- Tes: key terikat tidak bisa menulis ke bisnis lain; `business_name` palsu ditolak; key lama tetap berfungsi; agregat lintas bisnis mengecualikan demo; `include_demo` menyertakannya; MCP menjawab bisnis demo bila dipilih eksplisit; seed idempoten.

**Selesai bila:** 52 tes lama tetap hijau ditambah tes baru, dan Ashar bisa menunjukkan bahwa Overview tidak berubah setelah bisnis demo dibuat.

## 3. M1b: kendali demo (branch `feat/stage-m1b-demo-control`, setelah M1a disetujui)

- `app/services/demo_simulator_service.py`: memanggil `IngestionEngine` langsung. `scripts/demo_simulator.py` menjadi pembungkus CLI. Guard berbasis `is_demo`, bukan teks nama. Data simulator berganti ke tema **Talatee Skincare** (produk skincare, channel TikTok Shop, Shopee, Lazada, WhatsApp, Website) memakai daftar produk di prototipe sebagai acuan.
- Endpoint pemilik (sesi dashboard): `POST /showcase/simulator/trigger` (satu batch demo) dan `POST /showcase/reset`.
- Reset: pratinjau jumlah → konfirmasi → hapus; hanya bisnis `is_demo`; objek MinIO bisnis itu saja. **Pakai ulang pola `scripts/bulk_purge_test_businesses.py` dan `deletion_log` yang sudah ada**, jangan menulis penghapusan baru dari nol.
- Hubungkan kartu "Simulator data" dan "Reset demo" di `ShowcaseControl.jsx`.
- Tes: reset tidak pernah menyentuh bisnis non-demo; simulator menolak bisnis non-demo; endpoint ditolak tanpa sesi.

## 4. Urutan berikutnya (belum dikerjakan)

M2 (aturan kualitas dan domain baru) → M3 (pembersihan, tanpa hitung ulang subtotal) → M4 (upload banyak file demo + halaman Gudang Data) → M5 (ringkasan Panggung + `Stage.jsx`) → M6 (log Hermes + tool MCP stok/kampanye/channel).

Satu pekerjaan per branch, berhenti dan lapor di akhir tiap milestone, jangan merge tanpa persetujuan Ashar.
