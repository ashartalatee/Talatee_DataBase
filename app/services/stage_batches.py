"""Status file Gudang Data untuk Panggung, diturunkan dari status batch dan dataset yang nyata.
Murni (tanpa database) supaya mudah dites.

Pemetaan ke status yang dipahami tampilan Gudang Data:
  masuk     : baru masuk, belum diolah
  diproses  : sedang berjalan (baru saja berubah, dalam ACTIVE_WINDOW_MS)
  bersih    : lolos validasi (menunggu disetujui) atau sudah terpercaya
  tinjau    : gagal atau perlu ditinjau
Status kepercayaan asli tetap dikirim terpisah (field "trust") supaya layar bisa menulis
"Siap diverifikasi" untuk VALIDATING dan "Terpercaya" untuk TRUSTED dengan jujur.
"""

ACTIVE_WINDOW_MS = 45_000


def gudang_status(batch_status: str, trust: str, age_ms: int) -> str:
    if batch_status == "failed":
        return "tinjau"
    if batch_status == "running":
        return "diproses"
    if trust == "NEEDS_REVIEW":
        return "tinjau"
    if trust == "TRUSTED":
        return "bersih"
    if age_ms <= ACTIVE_WINDOW_MS:
        return "diproses" if trust in ("INGESTED", "VALIDATING") else "masuk"
    if trust == "VALIDATING":
        return "bersih"
    return "masuk"
