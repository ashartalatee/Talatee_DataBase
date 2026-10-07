"""
Pembersih baris: layer TERPISAH dari data asli (asli tidak disentuh).
Otomatis hanya untuk yang pasti: pangkas spasi tepi, samakan ejaan.
Sisanya masuk KARANTINA sampai manusia memutuskan (set_value / drop_row).
"""
from collections import Counter

from app.ingestion.issue_checks import check_rows, column_kind

AUTO_FIX = {"spasi_tepi", "ejaan_beda"}
RULE_LABEL = {
    "spasi_tepi": "Pangkas spasi di awal/akhir",
    "ejaan_beda": "Samakan ejaan ke yang paling umum",
}


def clean_rows(columns, rows, decisions=None):
    decisions = decisions or []

    # Keputusan terbaru per (baris, kolom); 'revert' membatalkan.
    latest = {}
    for d in decisions:
        latest[(d["row_number"], d.get("column_name") or "")] = d

    dropped, manual = {}, {}
    for (rn, ck), d in latest.items():
        if not (1 <= rn <= len(rows)):
            continue
        if d["action"] == "drop_row" and ck == "":
            dropped[rn] = d
        elif d["action"] == "set_value" and ck in columns:
            manual[(rn, ck)] = d

    work = [list(r) for r in rows]
    manual_changes = []
    for (rn, ck), d in manual.items():
        if rn in dropped:
            continue
        j = columns.index(ck)
        while len(work[rn - 1]) <= j:
            work[rn - 1].append("")
        before = work[rn - 1][j]
        work[rn - 1][j] = d.get("new_value") or ""
        manual_changes.append({
            "row": rn, "column": ck, "before": before, "after": work[rn - 1][j],
            "reason": d["reason"], "by": d.get("decided_by"), "at": d.get("decided_at"),
        })

    report = check_rows(columns, work)
    kinds = [column_kind(c) for c in columns]

    spelling = {}
    for j, k in enumerate(kinds):
        if k == "text":
            groups = {}
            for i, r in enumerate(work, start=1):
                if i in dropped:
                    continue
                if j < len(r) and r[j].strip():
                    groups.setdefault(r[j].strip().lower(), Counter())[r[j].strip()] += 1
            spelling[j] = {g: c.most_common(1)[0][0] for g, c in groups.items()}

    blockers = {}
    for it in report["issues"]:
        if it["type"] not in AUTO_FIX and it["row"] not in dropped:
            blockers.setdefault(it["row"], []).append(it)

    clean, quarantine, changes, dropped_list = [], [], [], []
    rule_cells = Counter()

    for i, r in enumerate(work, start=1):
        if i in dropped:
            d = dropped[i]
            dropped_list.append({
                "row": i, "values": rows[i - 1], "reason": d["reason"],
                "by": d.get("decided_by"), "at": d.get("decided_at"),
            })
            continue

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
            "dropped": len(dropped_list),
            "balanced": len(rows) == len(clean) + len(quarantine) + len(dropped_list),
        },
        "rules": [{"rule": k, "label": RULE_LABEL[k], "cells": rule_cells.get(k, 0)} for k in RULE_LABEL],
        "quarantine_by_type": dict(q_types),
        "clean": clean,
        "quarantine": quarantine,
        "dropped": dropped_list,
        "changes": changes,
        "manual_changes": manual_changes,
    }
