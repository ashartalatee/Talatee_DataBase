"""Kirim pesan ke Telegram lewat Bot API (sendMessage). Token dipakai bersama bot Hermes;
sendMessage tidak bentrok dengan polling getUpdates milik gateway Hermes.

DNS di PC ini kadang gagal untuk api.telegram.org (getaddrinfo failed), jadi kalau lewat
nama host gagal, dicoba alamat IP Telegram langsung. Sertifikat tetap diverifikasi terhadap
api.telegram.org (SNI)."""
import time

import httpx

from app.config import settings

API_HOST = "api.telegram.org"
FALLBACK_IPS = ("149.154.166.110", "149.154.167.220")


class TelegramError(Exception):
    pass


class _NetworkError(Exception):
    pass


def _post(path: str, payload: dict) -> httpx.Response:
    targets = [(f"https://{API_HOST}{path}", None)] + [(f"https://{ip}{path}", ip) for ip in FALLBACK_IPS]
    last = "tidak diketahui"
    for url, ip in targets:
        kwargs = {}
        if ip:
            kwargs = {"headers": {"Host": API_HOST}, "extensions": {"sni_hostname": API_HOST}}
        try:
            with httpx.Client(timeout=30) as client:
                return client.post(url, json=payload, **kwargs)
        except httpx.HTTPError as exc:
            # Hanya nama kelas: pesan httpx bisa memuat URL yang berisi token.
            last = type(exc).__name__
    raise _NetworkError(last)


def _send_one(text: str) -> int:
    token, chat_id = settings.telegram_bot_token, settings.telegram_chat_id
    if not token or not chat_id:
        raise TelegramError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID belum di-set.")
    path = f"/bot{token}/sendMessage"
    last = "tidak diketahui"
    for attempt in range(3):
        try:
            resp = _post(path, {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})
        except _NetworkError as exc:
            last = str(exc)
            time.sleep(2 * (attempt + 1))
            continue
        try:
            data = resp.json()
        except ValueError:
            data = {}
        if resp.status_code == 200 and data.get("ok"):
            return int(data["result"]["message_id"])
        if resp.status_code in (400, 401, 403, 404):
            # Salah konfigurasi: mengulang tidak akan membantu.
            raise TelegramError(f"Telegram menolak ({resp.status_code}): {data.get('description')}")
        last = f"HTTP {resp.status_code}"
        time.sleep(2 * (attempt + 1))
    raise TelegramError(f"Gagal mengirim ke Telegram: {last}")


def send_messages(texts: list[str]) -> list[int]:
    return [_send_one(t) for t in texts]