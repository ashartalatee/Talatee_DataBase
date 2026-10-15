"""
Pemeriksa kualitas baris mentah. HANYA membaca dan melaporkan masalah,
tidak pernah mengubah data. Tipe kolom ditebak dari nama kolom.
"""
import re
from collections import Counter
from datetime import datetime

DATE_HINTS = ("tanggal", "tgl", "date", "waktu")
NUM_HINTS = ("qty", "jumlah", "harga", "price", "subtotal", "total", "amount", "biaya")


def column_kind(name: str) -> str:
    n = name.strip().lower()
    if any(h in n for h in DATE_HINTS):
        return "date"
    if any(h in n for h in NUM_HINTS):
        return "number"
    return "text"


def _date_pattern(v: str):
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", v):
        return "YYYY-MM-DD"
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", v):
        return "DD/MM/YYYY"
    if re.fullmatch(r"\d{1,2}-\d{1,2}-\d{4}", v):
        return "DD-MM-YYYY"
    return None


def _date_valid(v: str, pattern: str) -> bool:
    try:
        if pattern == "YYYY-MM-DD":
            y, m, d = map(int, v.split("-"))
        elif pattern == "DD/MM/YYYY":
            d, m, y = map(int, v.split("/"))
        else:
            d, m, y = map(int, v.split("-"))
        datetime(y, m, d)
        return True
    except ValueError:
        return False


TIME_HINTS = ("waktu", "jam", "time", "pukul")
_DATE_STRICT = ("tanggal", "tgl", "date")
_CLOCK = r"\d{1,2}:\d{2}(?::\d{2})?"


def _time_valid(v: str) -> bool:
    """Jam sah: HH:MM atau HH:MM:SS, jam 0-23, menit dan detik 0-59."""
    if not re.fullmatch(_CLOCK, v):
        return False
    parts = [int(x) for x in v.split(":")]
    return parts[0] < 24 and all(x < 60 for x in parts[1:])


def _is_time_col(name: str) -> bool:
    """Kolom yang namanya menunjuk ke jam (waktu/jam), bukan ke tanggal."""
    n = name.strip().lower()
    return any(h in n for h in TIME_HINTS) and not any(h in n for h in _DATE_STRICT)


def _split_clock(v: str):
    """Pisahkan jam di ujung nilai: '2026-03-01 09:18' -> ('2026-03-01', '09:18'). Tanpa jam yang sah: (v, None)."""
    m = re.fullmatch(r"(.+?)[ T](" + _CLOCK + ")", v)
    if m and _time_valid(m.group(2)):
        return m.group(1), m.group(2)
    return v, None


def check_rows(columns: list[str], rows: list[list[str]]) -> dict:
    issues = []

    def add(row, col, typ, severity, message, value=""):
        issues.append({
            "row": row,
            "column": col,
            "type": typ,
            "severity": severity,
            "message": message,
            "value": value,
        })

    kinds = [column_kind(c) for c in columns]

    seen = {}
    for i, r in enumerate(rows, start=1):
        key = tuple(r)
        if key in seen:
            add(i, "", "duplikat", "warning", f"Sama persis dengan baris {seen[key]}")
        else:
            seen[key] = i

    dominant = {}
    for j, k in enumerate(kinds):
        if k == "date":
            pats = Counter(
                _date_pattern(_split_clock(r[j].strip())[0]) for r in rows
                if j < len(r) and r[j].strip() and _date_pattern(_split_clock(r[j].strip())[0])
            )
            if pats:
                dominant[j] = pats.most_common(1)[0][0]

    common_spelling = {}
    for j, k in enumerate(kinds):
        if k == "text":
            groups = {}
            for r in rows:
                if j < len(r) and r[j].strip():
                    groups.setdefault(r[j].strip().lower(), Counter())[r[j].strip()] += 1
            common_spelling[j] = {g: c.most_common(1)[0][0] for g, c in groups.items()}

    for i, r in enumerate(rows, start=1):
        for j, col in enumerate(columns):
            v = r[j] if j < len(r) else ""
            s = v.strip()

            if s == "":
                add(i, col, "kosong", "warning", "Sel kosong")
                continue

            if v != s:
                add(i, col, "spasi_tepi", "warning", "Ada spasi di awal/akhir", v)

            kind = kinds[j]
            if kind == "date":
                core, clock = _split_clock(s)
                if clock is None and _is_time_col(col) and _time_valid(s):
                    continue  # jam saja pada kolom waktu/jam: sah, bukan tanggal
                pat = _date_pattern(core)
                if pat is None:
                    add(i, col, "tanggal_tidak_dikenali", "error", "Format tanggal tidak dikenali", v)
                else:
                    if not _date_valid(core, pat):
                        add(i, col, "tanggal_mustahil", "error", "Tanggal tidak mungkin ada", v)
                    if j in dominant and pat != dominant[j]:
                        add(i, col, "format_tanggal_campur", "warning",
                            f"Format {pat}, mayoritas baris memakai {dominant[j]}", v)
            elif kind == "number":
                try:
                    num = float(s)
                except ValueError:
                    add(i, col, "bukan_angka", "error", "Kolom angka berisi teks", v)
                else:
                    if num < 0:
                        add(i, col, "angka_negatif", "error", "Angka negatif", v)
            else:
                best = common_spelling.get(j, {}).get(s.lower())
                if best is not None and s != best:
                    add(i, col, "ejaan_beda", "warning", f"Ejaan berbeda dari yang umum: '{best}'", v)

    by_type = Counter(x["type"] for x in issues)
    return {
        "total_rows": len(rows),
        "rows_with_issues": len({x["row"] for x in issues}),
        "total_issues": len(issues),
        "by_type": dict(by_type),
        "column_kinds": dict(zip(columns, kinds)),
        "issues": issues,
    }
