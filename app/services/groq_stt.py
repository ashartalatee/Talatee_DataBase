"""Transkripsi suara lewat Groq Whisper. Audio TIDAK disimpan: hanya lewat memori
lalu dibuang. Dipanggil dari backend (Vercel), jadi GROQ_API_KEY perlu di-set di sana.

Whisper bisa berhalusinasi pada audio hening/pendek (mengembalikan petunjuk kosakata
atau kalimat seperti 'terima kasih telah menonton'). clean_text() membuang segmen
seperti itu supaya tidak masuk ke jurnal."""
import re
import unicodedata

import httpx

from app.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = "whisper-large-v3-turbo"
# Batas request fungsi Vercel ~4,5 MB. Opus 32 kbps = ~2,4 MB per 10 menit.
MAX_AUDIO_BYTES = 4_000_000
MIN_AUDIO_BYTES = 1_000
# Daftar istilah (bukan kalimat) supaya lebih kecil kemungkinan digemakan.
VOCAB_HINT = "Hermes, Talatee, FastAPI, Groq, deploy, dashboard, Telegram, Vercel."

KNOWN_HALLUCINATIONS = (
    "terima kasih telah menonton",
    "terima kasih sudah menonton",
    "thanks for watching",
    "thank you for watching",
    "subtitles by",
    "subtitle by",
    "amara org",
    "sampai jumpa di video berikutnya",
)

EMPTY_MESSAGE = (
    "Tidak ada ucapan yang jelas terdeteksi. Cek mikrofon, lalu rekam lagi "
    "dengan suara lebih jelas dan lebih lama (minimal beberapa detik)."
)


class TranscribeError(Exception):
    pass


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _is_artifact(text: str) -> bool:
    n = _norm(text)
    if not n:
        return True
    if n in _norm(VOCAB_HINT):
        return True
    return len(n.split()) <= 8 and any(n.startswith(h) for h in KNOWN_HALLUCINATIONS)


def clean_text(data: dict) -> str:
    segments = data.get("segments") or []
    if not segments:
        text = (data.get("text") or "").strip()
        return "" if _is_artifact(text) else text
    kept = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if _is_artifact(text):
            continue
        if seg.get("no_speech_prob", 0) > 0.6 and seg.get("avg_logprob", 0) < -1.0:
            continue
        if seg.get("compression_ratio", 0) > 2.4:
            continue
        kept.append(text)
    return " ".join(kept).strip()


def extension_for(content_type: str) -> str:
    ct = (content_type or "").lower()
    if "mp4" in ct or "m4a" in ct or "aac" in ct:
        return "m4a"
    if "ogg" in ct:
        return "ogg"
    if "wav" in ct:
        return "wav"
    return "webm"


def transcribe(audio: bytes, content_type: str) -> str:
    if not settings.groq_api_key:
        raise TranscribeError("GROQ_API_KEY belum di-set di server.")
    filename = f"rekaman.{extension_for(content_type)}"
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                data={
                    "model": MODEL,
                    "language": "id",
                    "temperature": "0",
                    "response_format": "verbose_json",
                    "prompt": VOCAB_HINT,
                },
                files={"file": (filename, audio, content_type or "audio/webm")},
            )
    except httpx.HTTPError as exc:
        raise TranscribeError(f"Tidak bisa menghubungi layanan transkripsi ({type(exc).__name__}).") from exc
    if resp.status_code != 200:
        raise TranscribeError(f"Layanan transkripsi menolak rekaman (kode {resp.status_code}).")
    text = clean_text(resp.json())
    if not text:
        raise TranscribeError(EMPTY_MESSAGE)
    return text