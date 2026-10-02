// Data bagian Riset di Kompas. Ubah teks di sini, bukan di komponen.
export const DEFAULT_PRODUCTS = ["Jahe", "Kunyit", "Kakao & coklat", "Vanila"];
export const DAILY_TARGET = 3;
export const GATE = { minFindings: 20, perStage: 2 };

// Enam tahap dari hulu ke hilir. Dipakai untuk peta dan untuk mengelompokkan temuan.
export const STAGES = [
  { k: "hulu", n: "Budidaya", d: "Bibit, lahan, musim, sentra" },
  { k: "panen", n: "Panen dan pascapanen", d: "Sortasi, pengeringan, simpan" },
  { k: "olah", n: "Pengolahan dasar", d: "Irisan, bubuk, minyak, ekstrak" },
  { k: "setengah", n: "Setengah jadi", d: "Bahan baku industri" },
  { k: "jadi", n: "Produk jadi", d: "Sampai ke konsumen akhir" },
  { k: "pasar", n: "Pasar dan ekspor", d: "Harga, pembeli, aturan, pesaing" },
];

// Tiga pertanyaan per tahap. {p} diganti nama produk. Tiap hari dipilih 3 pertanyaan berurutan.
export const QUESTIONS = {
  hulu: ["Di provinsi mana {p} paling banyak ditanam, dan berapa produksi nasionalnya?", "Berapa hasil per hektare {p} dan berapa lama dari tanam sampai panen?", "Apa tantangan terbesar petani {p}: cuaca, hama, atau harga?"],
  panen: ["Bagaimana cara panen dan pascapanen {p} yang benar, dan berapa susut hasilnya?", "Apa standar mutu (misalnya kadar air) yang diminta pembeli {p}?", "Bagaimana penyimpanan {p} dan berapa lama masa simpannya?"],
  olah: ["Apa saja produk olahan dasar dari {p} (bubuk, minyak, ekstrak, dan lainnya)?", "Berapa rendemen {p}: berapa kg bahan mentah untuk 1 kg olahan?", "Mesin dan modal apa yang dibutuhkan untuk pengolahan dasar {p}?"],
  setengah: ["Industri apa yang membeli {p} setengah jadi sebagai bahan baku?", "Berapa selisih harga {p} mentah dan setengah jadi?", "Siapa pemain besar di Indonesia untuk {p} setengah jadi?"],
  jadi: ["Produk jadi dari {p} apa yang paling laku, dan siapa merek utamanya?", "Berapa margin produk jadi {p} dibanding bahan mentahnya?", "Peluang produk jadi {p} apa yang belum banyak digarap?"],
  pasar: ["Negara mana importir {p} terbesar, berapa nilainya, dan apa kode HS-nya?", "Sertifikasi atau aturan apa yang dibutuhkan untuk mengekspor {p} ke negara tujuan utama?", "Siapa pesaing ekspor {p} utama Indonesia dan apa keunggulannya?"],
};

// Enam kriteria "layak ditekuni", masing-masing diberi nilai 1 sampai 5.
export const CRITERIA = [
  { k: "permintaan", n: "Permintaan global", h: "Banyak importir dan tren naik" },
  { k: "margin", n: "Margin hilirisasi", h: "Selisih harga mentah ke jadi besar" },
  { k: "pasokan", n: "Pasokan dari Indonesia", h: "Bahan mudah didapat sepanjang tahun" },
  { k: "produksi", n: "Kemudahan produksi", h: "Modal, mesin, dan keahlian terjangkau" },
  { k: "regulasi", n: "Kemudahan regulasi", h: "Sertifikasi dan izin tidak rumit" },
  { k: "risiko", n: "Risiko rendah", h: "Harga dan cuaca stabil, pesaing wajar" },
];

// Kerangka umum jalur ekspor. Verifikasi ke Kemendag, Bea Cukai, dan eksportir berpengalaman.
export const EXPORT_STEPS = [
  "Legalitas usaha: NIB dan izin yang sesuai",
  "Tentukan kode HS, lalu cek tarif dan persyaratan di negara tujuan",
  "Cek standar mutu dan sertifikasi yang diminta pasar tujuan",
  "Cari 10 calon pembeli dan catat permintaan mereka: spesifikasi, volume, harga",
  "Buat sampel dan uji mutu di laboratorium",
  "Hitung harga: biaya produksi, kemasan, logistik, dan Incoterms",
  "Siapkan kemasan dan label sesuai negara tujuan",
  "Pilih forwarder dan pelajari dokumen ekspor",
  "Tentukan cara pembayaran dan kontrak dengan pembeli",
  "Kirim pesanan percobaan kecil, evaluasi, lalu perbesar",
];

// Kiriman harian. Contoh awal ini diambil dari satu artikel yang mengutip BPS (17 Juni 2026).
// Kiriman otomatis wajib diverifikasi ke sumber aslinya sebelum disimpan sebagai temuan.
const SRC = { source: "CNBC Indonesia Research, 17 Juni 2026 (mengutip BPS)", url: "https://www.cnbcindonesia.com/research/20260617135455-128-743389/ri-raja-rempah-tapi-jahe-impor-merajalela", date: "2026-10-02" };
export const FEED = [
  { id: "jahe-1", product: "Jahe", stage: "hulu", text: "Produksi jahe nasional 2025 tercatat 168,97 ribu ton, turun dari 307,24 ribu ton pada 2021. Produksinya masih terkonsentrasi di Pulau Jawa.", ...SRC },
  { id: "jahe-2", product: "Jahe", stage: "pasar", text: "Nilai ekspor jahe Indonesia 2025 hanya US$3,88 juta. Volumenya 2.619 ton, turun dari 8.229 ton pada 2024. Tujuan terbesar: Amerika Serikat (US$0,99 juta).", ...SRC },
  { id: "jahe-3", product: "Jahe", stage: "pasar", text: "Nilai impor jahe 2025 mencapai US$11,61 juta (naik 51,7%), hampir tiga kali nilai ekspor. Pemasok terbesar: Thailand (US$4,31 juta) dan Vietnam (US$4,11 juta).", ...SRC },
];
export const NOTES = {
  Jahe: "Catatan awal (hipotesis, belum terbukti): untuk jahe segar, Indonesia kini lebih banyak mengimpor daripada mengekspor. Peluang ekspor kemungkinan ada di nilai tambah (olahan), bukan jahe mentah. Buktikan dengan data tahap pengolahan dan produk jadi.",
};
