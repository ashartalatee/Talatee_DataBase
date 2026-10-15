from app.ingestion.clean_rows import clean_rows
from app.ingestion.issue_checks import check_rows


def types(report):
    return [i["type"] for i in report["issues"]]


def test_jam_saja_pada_kolom_waktu_sah():
    r = check_rows(["order_id", "waktu"], [["A1", "09:18"], ["A2", "23:59:59"], ["A3", "0:05"]])
    assert r["issues"] == []


def test_jam_saja_pada_kolom_tanggal_tetap_dilaporkan():
    r = check_rows(["order_id", "tanggal"], [["A1", "09:18"]])
    assert types(r) == ["tanggal_tidak_dikenali"]


def test_jam_yang_tidak_mungkin_dilaporkan():
    r = check_rows(["order_id", "waktu"], [["A1", "25:61"], ["A2", "24:00"]])
    assert types(r) == ["tanggal_tidak_dikenali", "tanggal_tidak_dikenali"]


def test_tanggal_dan_jam_sekaligus_sah_dan_tidak_dianggap_campur():
    rows = [["A1", "2026-03-01 09:18"], ["A2", "2026-03-02T10:30:15"], ["A3", "2026-03-03 8:05"]]
    assert check_rows(["id", "waktu"], rows)["issues"] == []
    assert check_rows(["id", "tanggal"], rows)["issues"] == []


def test_bagian_tanggal_pada_gabungan_tetap_diperiksa():
    assert types(check_rows(["id", "tanggal"], [["A1", "2026-02-31 09:18"]])) == ["tanggal_mustahil"]


def test_jam_salah_pada_gabungan_dilaporkan():
    assert types(check_rows(["id", "tanggal"], [["A1", "2026-03-01 25:99"]])) == ["tanggal_tidak_dikenali"]


def test_format_tanggal_campur_tetap_terdeteksi():
    rows = [["A1", "2026-03-01"], ["A2", "2026-03-02"], ["A3", "02/03/2026"]]
    assert types(check_rows(["id", "tanggal"], rows)) == ["format_tanggal_campur"]


def test_perilaku_lama_tidak_berubah():
    rows = [["A1", "abc", "Serum"], ["A2", "-1", "serum"], ["A1", "abc", "Serum"], ["A4", "", "Serum"]]
    r = check_rows(["id", "qty", "produk"], rows)
    assert r["by_type"] == {"duplikat": 1, "bukan_angka": 2, "angka_negatif": 1, "ejaan_beda": 1, "kosong": 1}


def test_clean_rows_tidak_lagi_mengarantina_kolom_waktu():
    cols = ["order_id", "tanggal", "waktu"]
    rows = [["A1", "2026-03-01", "09:18"], ["A2", "2026-03-02", "11:42"]]
    rec = clean_rows(cols, rows)["reconciliation"]
    assert rec["clean"] == 2 and rec["quarantine"] == 0
