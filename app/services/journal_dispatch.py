"""Pengiriman hook: ambil jurnal yang jatuh tempo, minta Hermes, kirim ke Telegram.

Dijalankan oleh scripts/journal_dispatch.py (Task Scheduler di PC). Aman dijalankan
bersamaan atau berulang: 'klaim' memakai UPDATE atomik (FOR UPDATE SKIP LOCKED), dan
status 'sent' tidak pernah diproses lagi."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.kompas_journal import MAX_ATTEMPTS, KompasJournal
from app.services.journal_hooks import format_messages, generate_hooks
from app.services.telegram import send_messages

STUCK_AFTER_MINUTES = 30
RETRY_STEP_MINUTES = 10


def scrub(msg: str) -> str:
    for secret in (settings.telegram_bot_token, settings.groq_api_key, settings.hermes_api_key):
        if secret:
            msg = msg.replace(secret, "***")
    return msg


def claim_next(db: Session, only_username: str | None = None):
    extra, params = "", {}
    if only_username:
        extra, params = "AND username = :u", {"u": only_username}
    row = db.execute(
        text(
            f"""
            UPDATE kompas_journals
               SET status = 'processing', attempts = attempts + 1, claimed_at = now()
             WHERE id = (
                SELECT id FROM kompas_journals
                 WHERE ((status = 'pending' AND send_at <= now())
                    OR (status = 'processing'
                        AND claimed_at < now() - interval '{STUCK_AFTER_MINUTES} minutes'))
                   {extra}
                 ORDER BY send_at
                 LIMIT 1
                 FOR UPDATE SKIP LOCKED)
            RETURNING id
            """
        ),
        params,
    ).first()
    db.commit()
    return row[0] if row else None


def _recent_hooks(db: Session, j: KompasJournal) -> list[str]:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = (
        db.query(KompasJournal.hooks)
        .filter(
            KompasJournal.username == j.username,
            KompasJournal.status == "sent",
            KompasJournal.sent_at >= since,
            KompasJournal.hooks.isnot(None),
        )
        .all()
    )
    return [h["hook"] for (hooks,) in rows for h in hooks if isinstance(h, dict) and "hook" in h][:35]


def process_one(db: Session, journal_id, generate=generate_hooks, send=send_messages) -> str:
    j = db.get(KompasJournal, journal_id)
    try:
        hooks = j.hooks
        if not hooks:  # percobaan ulang setelah Telegram gagal tidak memanggil Hermes lagi
            hooks = generate(j.edited_text, _recent_hooks(db, j))
            j.hooks = hooks
            db.commit()
        ids = send(format_messages(hooks, j.created_at))
        j.status = "sent"
        j.sent_at = datetime.now(timezone.utc)
        j.telegram_message_id = ids[0] if ids else None
        j.error = None
        db.commit()
        return "sent"
    except Exception as exc:  # noqa: BLE001 - semua kegagalan dicatat, tidak ada hasil setengah jadi terkirim
        db.rollback()
        j = db.get(KompasJournal, journal_id)
        j.error = scrub(f"{type(exc).__name__}: {exc}")[:500]
        if j.attempts >= MAX_ATTEMPTS:
            j.status = "failed"
        else:
            j.status = "pending"
            j.send_at = datetime.now(timezone.utc) + timedelta(minutes=RETRY_STEP_MINUTES * j.attempts)
        db.commit()
        return j.status


def run_due(db: Session, max_items: int = 3, only_username: str | None = None, **kw) -> list[tuple]:
    results = []
    for _ in range(max_items):
        jid = claim_next(db, only_username)
        if jid is None:
            break
        results.append((jid, process_one(db, jid, **kw)))
    return results
