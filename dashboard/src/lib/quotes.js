// Pemantik harian untuk Kompas. Semua kalimat ditulis untuk perjalananmu sendiri,
// sebagian memakai kata-katamu dari infografik. Sengaja tanpa nama tokoh.
// Ubah, tambah, atau hapus kalimat dengan bebas. Tiap daftar berputar per hari.

const MULAI = [
  'Hari ini tidak perlu sempurna. Cukup mulai dari satu hal kecil.',
  'Satu baris kode hari ini lebih berharga daripada seribu rencana besok.',
  'Kebiasaan dibangun oleh hari-hari biasa, bukan hari-hari istimewa.',
  'Jangan menunggu mood. Mulai dulu, semangatnya menyusul.',
  'Versi terbaikmu di 2027 sedang dibentuk oleh keputusan kecil pagi ini.',
  'Buka proyekmu. Kerjakan satu hal. Sisanya akan mengikuti.',
  'Yang membedakan bukan bakat, tapi siapa yang tetap muncul setiap hari.',
  'Mulai dari yang paling mudah. Momentum lahir dari gerakan pertama.',
  'Sistem yang kamu bangun hari ini akan bekerja untukmu di hari-hari kamu lelah.',
  'Ada ide bidang lain yang menggoda? Catat di Parkir ide, lalu kembali ke jalurmu.',
  'Totalitas adalah hadir sepenuh hati hari ini, bukan memaksa diri sampai habis.',
  'Sedikit lebih baik setiap hari, akan menjadi perubahan besar di 2027.',
  'Kamu tidak perlu menjadi sempurna. Kamu hanya perlu lebih baik dari kemarin.',
  'Bukan soal seberapa cepat kamu sampai, tapi seberapa dalam kamu menguasai jalan ini.',
  'Satu spesialisasi. Banyak peluang. Dampak yang nyata.',
  'Eksplorasi boleh, fokus tetap.',
]

const LANJUT = [
  'Sudah mulai, itu bagian tersulit. Tinggal diteruskan.',
  'Satu lagi. Rantai ini dibangun dari mata rantai yang kecil.',
  'Sisa yang kecil inilah yang membedakan hari biasa dari hari yang dituntaskan.',
  'Kamu lebih dekat dari yang terasa.',
  'Kerjakan yang tersisa dengan tenang. Tidak perlu terburu-buru, cukup tuntaskan.',
  'Konsistensi terlihat membosankan dari luar, dan luar biasa dari dalam.',
  'Energi yang sudah terbentuk jangan disia-siakan. Lanjutkan selagi hangat.',
  'Kemajuan kecil yang berulang mengalahkan lonjakan besar yang sesekali.',
  'Kamu tidak sedang mengejar orang lain. Kamu sedang melampaui dirimu yang kemarin.',
  'Satu langkah lagi dan hari ini sudah menang.',
  'Fokus + Adaptasi = Unggul.',
  'Komunikasi = Dampak. Ceritakan apa yang kamu kerjakan hari ini.',
  'Jangan bandingkan awal perjalananmu dengan pertengahan perjalanan orang lain.',
  'Teknologi adalah alat, tapi kamu adalah penggunanya.',
]

const TUNTAS = [
  'Hari ini tuntas. Istirahatlah tanpa rasa bersalah, kamu sudah menepati dirimu sendiri.',
  'Tiga dari tiga. Beginilah versi terbaikmu dibangun, diam-diam dan berulang.',
  'Rantai hari ini aman. Besok cukup ulangi.',
  'Menepati janji pada diri sendiri adalah fondasi semua pencapaian.',
  'Satu hari yang tuntas memang kecil. Seratus hari seperti ini mengubah hidup.',
  'Boleh bangga. Jangan berhenti. Besok kita lanjutkan dengan tenang.',
  'Yang kamu kerjakan hari ini akan berterima kasih padamu di bulan Januari.',
  'Tidur yang cukup adalah bagian dari latihan.',
  'Kamu bukan hanya menyelesaikan tugas. Kamu memperkuat kepercayaan pada dirimu sendiri.',
  'Tutup laptop dengan tenang. Pikiran yang beristirahat ikut bekerja untuk besok.',
  'Hari ini kamu sudah memilih jalanmu lagi. Itu yang terpenting.',
  'Bangun sistem, cipta dampak. Hari ini kamu sudah melakukan bagianmu.',
]

const AKHIR_PEKAN = [
  'Akhir pekan untuk menoleh ke belakang sebentar, lalu menata langkah ke depan.',
  'Tidak semua kemajuan terlihat. Sebagian terjadi saat kamu beristirahat dan merenung.',
  'Review singkat hari ini menghemat banyak salah arah minggu depan.',
  'Totalitas bukan berarti tanpa jeda. Atlet terbaik pun punya hari pemulihan.',
  'Apa yang kamu pelajari minggu ini? Tulis, supaya tidak hilang.',
  'Jaga tubuh dan pikiran. Keduanya adalah alat terpentingmu.',
  'Istirahat yang baik adalah bagian dari kerja yang baik.',
  'Kamu tidak harus mengerjakan semuanya. Cukup pastikan yang terpenting tetap berjalan.',
  'Jaga ritme, jaga energi, jaga tujuan.',
]

// Muncul tepat di hari rantai sebuah kebiasaan mencapai angka ini (dan kebiasaan itu sudah dicentang hari ini).
const STREAK_LINES = {
  3: 'Tiga hari berturut-turut. Ritmenya mulai terbentuk.',
  7: 'Seminggu penuh. Ini bukan lagi kebetulan, ini mulai menjadi kebiasaan.',
  14: 'Dua minggu tanpa putus. Kamu sedang membangun identitas yang baru.',
  21: 'Tiga minggu berturut-turut. Kebiasaan ini sudah punya akar.',
  30: 'Tiga puluh hari. Yang dulu terasa berat kini terasa biasa, dan itu tanda kemajuan.',
  60: 'Dua bulan konsisten. Kamu sudah bukan orang yang mencoba, kamu orang yang menjalani.',
  100: 'Seratus hari. Ini bukan lagi percobaan, ini sudah bagian dari dirimu.',
}

// Muncul tepat pada sisa hari ini menuju 1 Januari 2027.
const COUNTDOWN_LINES = {
  90: 'Sembilan puluh hari menuju 2027. Masih banyak waktu untuk membentuk ritme yang kokoh.',
  60: 'Dua bulan lagi. Jaga ritme, jangan menambah beban baru.',
  30: 'Tinggal sebulan. Ritme yang kamu bangun sekarang akan terbawa ke tahun depan.',
  14: 'Dua minggu lagi menuju 2027. Kamu sudah jauh lebih siap daripada saat memulai.',
  7: 'Seminggu lagi. Nikmati prosesnya, bukan hanya hasilnya.',
  3: 'Tiga hari lagi. Bukan garis finis, hanya pintu menuju babak berikutnya.',
  1: 'Besok 1 Januari 2027. Kebiasaanmu sudah menunggu di sana.',
  0: 'Hari ini 1 Januari 2027. Kebiasaan ini sekarang milikmu.',
}

export const POOLS = { mulai: MULAI, lanjut: LANJUT, tuntas: TUNTAS, akhirPekan: AKHIR_PEKAN }
export { STREAK_LINES, COUNTDOWN_LINES }

const DAY = 864e5

/** Nomor hari (bilangan bulat) berdasarkan tanggal lokal, stabil sepanjang hari. */
export function dayNumber(d = new Date()) {
  return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY)
}

const rotate = (pool, dn, salt) => pool[(dn + salt) % pool.length]

/**
 * Memilih kalimat hari ini.
 * done    : jumlah kebiasaan yang sudah dicentang hari ini (0-3)
 * streaks : rantai (hari) dari kebiasaan yang SUDAH dicentang hari ini
 * left    : sisa hari menuju 1 Januari 2027
 * Prioritas: tonggak rantai > hari penting menuju 2027 > keadaan hari ini.
 */
export function pickQuote({ done = 0, streaks = [], left = 999, date = new Date() } = {}) {
  const dn = dayNumber(date)
  const milestone = Math.max(0, ...streaks.filter((s) => STREAK_LINES[s]))
  if (milestone) return { kind: 'streak', text: STREAK_LINES[milestone] }
  if (COUNTDOWN_LINES[left]) return { kind: 'countdown', text: COUNTDOWN_LINES[left] }
  if (done >= 3) return { kind: 'tuntas', text: rotate(TUNTAS, dn, 5) }
  const dow = date.getDay()
  if (dow === 0 || dow === 6) return { kind: 'akhirPekan', text: rotate(AKHIR_PEKAN, dn, 2) }
  if (done === 0) return { kind: 'mulai', text: rotate(MULAI, dn, 0) }
  return { kind: 'lanjut', text: rotate(LANJUT, dn, 3) }
}
