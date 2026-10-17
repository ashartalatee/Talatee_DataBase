"""Kejadian dan langkah agen untuk Panggung, diturunkan dari status batch dan dataset di database.

Tidak ada yang dikarang: tiap kejadian berasal dari baris nyata (batch dan status kepercayaan dataset).
Langkah agen diturunkan dari status saat ini:
  batch running             -> read      (file sedang dibaca)
  batch sukses + INGESTED   -> clean     (data dirapikan)
  VALIDATING                -> validate  (diperiksa aturan, menunggu keputusan percaya)
  TRUSTED (baru saja)       -> trust     (baru ditetapkan, tampil beberapa detik)
Batch yang sudah lama (lewat ACTIVE_WINDOW_MS) tidak dianggap sedang diproses.
Fungsi di sini murni (tanpa database) supaya mudah dites.
"""
from dataclasses import dataclass

ACTIVE_WINDOW_MS = 45_000
JUST_DONE_MS = 6_000
MAX_EVENTS = 40


@dataclass
class ActivityRow:
    batch_id: str
    dataset_id: str
    filename: str
    channel: str
    batch_status: str
    records: int
    trust: str
    started_ms: int
    finished_ms: int | None = None
    updated_ms: int | None = None


def _state_event(r: ActivityRow):
    t = max(r.started_ms, r.finished_ms or 0, r.updated_ms or 0) + 1
    base = {"t": t, "batchId": r.batch_id}
    if r.batch_status == "failed":
        return {**base, "kind": "info", "tone": "y", "text": f"{r.filename} gagal diproses"}
    if r.batch_status == "running":
        return None
    if r.trust == "TRUSTED":
        return {**base, "kind": "trust", "tone": "g", "text": f"Terpercaya: {r.records} baris dari {r.filename} masuk ke omzet"}
    if r.trust == "NEEDS_REVIEW":
        return {**base, "kind": "trust", "tone": "y", "text": f"{r.filename} perlu ditinjau, belum dihitung ke omzet"}
    if r.trust == "VALIDATING":
        return {**base, "kind": "validate", "tone": "y", "text": f"Memeriksa aturan data {r.filename}"}
    if r.trust == "INGESTED":
        return {**base, "kind": "clean", "tone": "y", "text": f"Merapikan data {r.filename}"}
    return None


def _agent(rows, now_ms: int) -> dict:
    newest = rows[0] if rows else None
    idle = {
        "status": "idle",
        "step": None,
        "batchId": newest.batch_id if newest else None,
        "label": "",
        "lastDone": bool(newest and newest.batch_status != "failed" and newest.trust == "TRUSTED"),
    }
    for r in rows:
        age = now_ms - max(r.started_ms, r.finished_ms or 0, r.updated_ms or 0)
        step = label = None
        if r.batch_status == "running" and age <= ACTIVE_WINDOW_MS:
            step, label = "read", f"Membaca {r.filename}"
        elif r.batch_status in ("success", "partial_failed"):
            if r.trust == "INGESTED" and age <= ACTIVE_WINDOW_MS:
                step, label = "clean", f"Merapikan {r.filename}"
            elif r.trust == "VALIDATING" and age <= ACTIVE_WINDOW_MS:
                step, label = "validate", f"Memeriksa aturan di {r.filename}"
            elif r.trust == "TRUSTED" and age <= JUST_DONE_MS:
                step, label = "trust", f"Menetapkan status {r.filename}"
        if step:
            return {"status": "working", "step": step, "batchId": r.batch_id, "label": label, "lastDone": False}
    return idle


def build_activity(rows, now_ms: int):
    """rows: ActivityRow, terbaru di atas. Mengembalikan (events, agent)."""
    events = []
    seen = set()
    for r in rows:
        events.append({
            "t": r.started_ms, "kind": "file", "tone": "b", "batchId": r.batch_id,
            "text": f"Menemukan file baru: {r.filename} ({r.channel})",
        })
        if r.dataset_id in seen:  # status kepercayaan itu milik dataset: hanya batch terbarunya yang dilaporkan
            continue
        seen.add(r.dataset_id)
        ev = _state_event(r)
        if ev:
            events.append(ev)
    events.sort(key=lambda e: e["t"], reverse=True)
    return events[:MAX_EVENTS], _agent(rows, now_ms)
