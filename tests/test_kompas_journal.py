"""Tes jurnal suara. Memakai Postgres lokal (talatee_test) seperti tes Kompas lain.
Migrasi harus sudah diterapkan ke DATABASE TES (lihat langkah di panduan).
Groq, Hermes, dan Telegram di-fake: tidak ada panggilan jaringan.

  python -m pytest tests/test_kompas_journal.py -v
"""
import secrets
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.kompas_checkin import KompasCheckin
from app.models.kompas_journal import KompasJournal
from app.security.dashboard_session import require_dashboard_session
from app.services import journal_dispatch as jd
from app.services.journal_hooks import (
    HookGenerationError,
    format_messages,
    generate_hooks,
    validate_hooks,
)

client = TestClient(app)

TRANSCRIPT = (
    "Hari ini saya buang tiga jam karena satu baris config yang salah di deploy. "
    "Saya sadar tools canggih saja tidak cukup kalau saya belum tahu masalah yang ingin diselesaikan."
)


def _hooks(n=5):
    quotes = [
        "buang tiga jam karena satu baris config",
        "tools canggih saja tidak cukup",
        "belum tahu masalah yang ingin diselesaikan",
        "satu baris config yang salah di deploy",
        "saya sadar tools canggih saja",
    ]
    return [
        {"hook": f"Hook nomor {i} yang spesifik", "pola": "cerita kegagalan", "alasan": "Alasan singkat. Relevan.",
         "kutipan": quotes[i], "format": "Reels"}
        for i in range(n)
    ]


@pytest.fixture
def me():
    name = f"journal_test_{secrets.token_hex(4)}"
    app.dependency_overrides[require_dashboard_session] = lambda: name
    yield name
    app.dependency_overrides.pop(require_dashboard_session, None)
    db = SessionLocal()
    db.query(KompasJournal).filter(KompasJournal.username == name).delete()
    db.query(KompasCheckin).filter(KompasCheckin.username == name).delete()
    db.commit()
    db.close()


def _create(text=TRANSCRIPT):
    return client.post(
        "/kompas/journals",
        json={"raw_transcript": text, "text": text, "day": date.today().isoformat(), "duration_seconds": 90},
    )


def _make_due(journal_id):
    db = SessionLocal()
    j = db.get(KompasJournal, journal_id)
    j.send_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    db.close()


# ---------- API ----------

def test_create_sets_send_at_three_hours_ahead_and_checks_speaking(me):
    r = _create()
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    delta = datetime.fromisoformat(body["send_at"]) - datetime.now(timezone.utc)
    assert timedelta(hours=2, minutes=58) < delta < timedelta(hours=3, minutes=1)
    checkins = client.get("/kompas/checkins").json()
    assert date.today().isoformat() in checkins["speaking"]


def test_create_rejects_too_short_and_future_day(me):
    assert _create("pendek").status_code == 400
    far = (date.today() + timedelta(days=5)).isoformat()
    r = client.post("/kompas/journals", json={"raw_transcript": TRANSCRIPT, "text": TRANSCRIPT, "day": far})
    assert r.status_code == 400


def test_raw_transcript_is_kept_separate_from_edited_text(me):
    r = client.post(
        "/kompas/journals",
        json={"raw_transcript": "mentah asli " + TRANSCRIPT, "text": TRANSCRIPT, "day": date.today().isoformat()},
    )
    db = SessionLocal()
    j = db.get(KompasJournal, r.json()["id"])
    assert j.raw_transcript.startswith("mentah asli") and j.edited_text == TRANSCRIPT
    db.close()


def test_transcribe_endpoint_validations(me, monkeypatch):
    from app.api.routes import kompas_journals as route

    monkeypatch.setattr(route, "transcribe", lambda audio, ct: "halo dunia")
    ok = client.post("/kompas/journals/transcribe", files={"file": ("r.webm", b"x" * 2000, "audio/webm")})
    assert ok.status_code == 200 and ok.json()["text"] == "halo dunia"
    short = client.post("/kompas/journals/transcribe", files={"file": ("r.webm", b"x" * 10, "audio/webm")})
    assert short.status_code == 400
    big = client.post("/kompas/journals/transcribe", files={"file": ("r.webm", b"x" * 4_000_001, "audio/webm")})
    assert big.status_code == 413


def test_delete_only_own_journal(me):
    jid = _create().json()["id"]
    assert client.delete(f"/kompas/journals/{jid}").status_code == 204
    assert client.get("/kompas/journals").json() == []


# ---------- validasi hook ----------

def test_validate_hooks_drops_quotes_not_in_transcript():
    hooks = _hooks(2)
    hooks[1]["kutipan"] = "kutipan karangan yang tidak ada di jurnal"
    good, bad = validate_hooks(hooks, TRANSCRIPT)
    assert len(good) == 1 and len(bad) == 1


def test_generate_hooks_retries_once_then_fails():
    calls = []

    def ask(messages):
        calls.append(1)
        return '{"hooks": []}'

    with pytest.raises(HookGenerationError):
        generate_hooks(TRANSCRIPT, [], ask=ask)
    assert len(calls) == 2


def test_generate_hooks_accepts_json_wrapped_in_text():
    import json

    raw = "Ini hasilnya:\n```json\n" + json.dumps({"hooks": _hooks(5)}) + "\n```"
    assert len(generate_hooks(TRANSCRIPT, [], ask=lambda m: raw)) == 5


def test_telegram_message_has_hooks_but_not_raw_journal():
    msgs = format_messages(_hooks(5), datetime.now(timezone.utc))
    assert all(len(m) <= 4096 for m in msgs)
    joined = "\n".join(msgs)
    assert "Kenapa kuat" in joined and TRANSCRIPT not in joined


# ---------- pengiriman ----------

def test_dispatch_sends_once_even_if_run_twice(me):
    jid = _create().json()["id"]
    _make_due(jid)
    sent = []

    def fake_send(texts):
        sent.append(texts)
        return [111]

    db = SessionLocal()
    first = jd.run_due(db, only_username=me, generate=lambda t, h: _hooks(5), send=fake_send)
    second = jd.run_due(db, only_username=me, generate=lambda t, h: _hooks(5), send=fake_send)
    j = db.get(KompasJournal, jid)
    assert [s for _, s in first] == ["sent"] and second == []
    assert len(sent) == 1 and j.status == "sent" and j.telegram_message_id == 111
    db.close()


def test_not_due_journal_is_not_processed(me):
    _create()
    db = SessionLocal()
    assert jd.run_due(db, only_username=me, generate=lambda t, h: _hooks(5), send=lambda t: [1]) == []
    db.close()


def test_failed_telegram_keeps_hooks_and_retries_without_calling_hermes_again(me):
    jid = _create().json()["id"]
    _make_due(jid)
    hermes_calls = []

    def gen(t, h):
        hermes_calls.append(1)
        return _hooks(5)

    def broken_send(texts):
        raise RuntimeError("telegram down")

    db = SessionLocal()
    assert [s for _, s in jd.run_due(db, only_username=me, generate=gen, send=broken_send)] == ["pending"]
    j = db.get(KompasJournal, jid)
    assert j.attempts == 1 and j.hooks and "telegram down" in j.error
    assert j.send_at > datetime.now(timezone.utc)  # ditunda, bukan langsung diulang
    _make_due(jid)
    db.expire_all()
    assert [s for _, s in jd.run_due(db, only_username=me, generate=gen, send=lambda t: [5])] == ["sent"]
    assert len(hermes_calls) == 1
    db.close()


def test_journal_becomes_failed_after_max_attempts(me):
    jid = _create().json()["id"]
    db = SessionLocal()
    j = db.get(KompasJournal, jid)
    j.attempts = 5
    j.send_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    def broken(t, h):
        raise HookGenerationError("hermes mati")

    assert [s for _, s in jd.run_due(db, only_username=me, generate=broken, send=lambda t: [1])] == ["failed"]
    db.close()
