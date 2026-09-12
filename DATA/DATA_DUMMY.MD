Buatkan data dummy transaksi restoran/warung untuk tanggal {TANGGAL_HARI_INI, format YYYY-MM-DD}
dalam format CSV, siap upload ke sistem saya. Ketentuan:

KOLOM (persis, header di baris pertama):
order_id,tanggal,produk,kategori,qty,harga_satuan,subtotal,status

ATURAN ISI:
- order_id: HARUS unik dan menyertakan tanggal, format ORD-{YYYYMMDD}-{nomor urut 3 digit}
  (misal ORD-20260908-001). JANGAN pernah pakai pola order_id yang sama dari hari
  sebelumnya (nomor urut boleh mulai dari 001 lagi tiap hari, tapi tanggalnya beda
  jadi tetap unik keseluruhan).
- tanggal: sama persis dengan tanggal yang saya minta, format YYYY-MM-DD, untuk SEMUA baris.
- produk: nama menu restoran/warung yang wajar (nasi goreng, ayam geprek, es teh, dll),
  variasikan.
- kategori: makanan / minuman / snack.
- qty: angka wajar 1-5.
- harga_satuan: harga wajar rupiah (5000-45000), angka bulat tanpa titik/koma pemisah ribuan.
- subtotal: HARUS PERSIS qty x harga_satuan (jangan salah hitung, ini divalidasi otomatis).
- status: variasikan realistis — sekitar 85% "Completed", 10% "Pending", 5% "Cancelled".

JUMLAH: buatkan {JUMLAH_TRANSAKSI, misal 30-50} baris transaksi untuk hari itu.

Keluarkan HANYA isi CSV mentah (bisa langsung saya save jadi file .csv), tanpa
penjelasan atau teks tambahan sebelum/sesudahnya.