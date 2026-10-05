"""
Pembersih baris: menghasilkan layer TERPISAH dari data asli (asli tidak disentuh).
Perbaikan otomatis hanya untuk yang pasti: pangkas spasi tepi, samakan ejaan.
Baris dengan masalah lain (kosong, duplikat, angka/tanggal janggal, format campur)
masuk KARANTINA: tidak ditebak, tidak dihapus.
"""
from collections import Counter

from app.ingestion.issue_checks import check_rows, column_kind

AUTO_FIX = {"spasi_tepi", "ejaan_beda"}
RULE_LABEL = {
    "spasi_tepi": "Pangkas spasi di awal/akhir",
    "ejaan_beda": "Samakan ejaan ke yang paling umum",
}


def clean_rows(columns: list[str], rows: list[list[str]]) -> dict:
    report = check_rows(columns, rows)
    kinds = [column_kind(c) for c in columns]

    spelling = {}
    for j, k in enumerate(kinds):
        if k == "text":
            groups = {}
            for r in rows:
                if j < len(r) and r[j].strip():
                    groups.setdefault(r[j].strip().lower(), Counter())[r[j].strip()] += 1
            spelling[j] = {g: c.most_common(1)[0][0] for g, c in groups.items()}

    blockers = {}
    for it in report["issues"]:
        if it["type"] not in AUTO_FIX:
            blockers.setdefault(it["row"], []).append(it)

    clean, quarantine, changes = [], [], []
    rule_cells = Counter()

    for i, r in enumerate(rows, start=1):
        if i in blockers:
            quarantine.append({
                "row": i,
                "values": r,
                "reasons": [
                    {"column": x["column"], "type": x["type"], "message": x["message"], "value": x["value"]}
                    for x in blockers[i]
                ],
            })
            continue

        new = []
        for j, col in enumerate(columns):
            v = r[j] if j < len(r) else ""
            s = v.strip()
            applied = []
            if s != v:
                applied.append("spasi_tepi")
            after = s
            if kinds[j] == "text" and s:
                best = spelling.get(j, {}).get(s.lower())
                if best and best != s:
                    applied.append("ejaan_beda")
                    after = best
            if applied:
                changes.append({"row": i, "column": col, "before": v, "after": after, "rules": applied})
                for a in applied:
                    rule_cells[a] += 1
            new.append(after)
        clean.append({"row": i, "values": new})

    q_types = Counter(x["type"] for q in quarantine for x in q["reasons"])
    return {
        "columns": columns,
        "reconciliation": {
            "original": len(rows),
            "clean": len(clean),
            "quarantine": len(quarantine),
            "dropped": 0,
            "balanced": len(rows) == len(clean) + len(quarantine),
        },
        "rules": [
            {"rule": k, "label": RULE_LABEL[k], "cells": rule_cells.get(k, 0)} for k in RULE_LABEL
        ],
        "quarantine_by_type": dict(q_types),
        "clean": clean,
        "quarantine": quarantine,
        "changes": changes,
    }
