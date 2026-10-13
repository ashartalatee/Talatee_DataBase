"""Menyusun 5 hook dari jurnal lewat Hermes, memvalidasinya, dan memformat pesan Telegram.

Hermes hanya MENULIS hook. Kode di sini yang memeriksa: setiap hook wajib membawa
kutipan yang benar-benar ada di jurnal. Hook tanpa sumber yang cocok dibuang."""
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

MIN_HOOKS = 5
WIB = timezone(timedelta(hours=7))
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
FIELDS = ("hook", "pola", "alasan", "kutipan", "format")
TELEGRAM_CHUNK = 3900  # batas Telegram 4096 karakter

SYSTEM_PROMPT = """Kamu adalah content strategist untuk Ashar (Talatee). Kamu akan menerima jurnal suara
Ashar hari ini, murni ucapannya sendiri. Jangan memakai tool apa pun. Balas HANYA dengan JSON.

Tugas: buat 5 hook konten yang paling tepat dari jurnal ini.

Aturan:
- Setiap hook harus berpijak pada detail SPESIFIK di jurnal (angka, kejadian, kesalahan, penemuan).
  Dilarang hook generik yang bisa dipakai siapa saja.
- Pakai gaya bahasa Ashar yang santai dan jujur. Pertahankan frasa khasnya.
- Pilih pola yang cocok dengan isi jurnal: curiosity gap, contrarian, cerita kegagalan,
  hasil berangka, atau yang tidak diceritakan orang lain. Pola boleh berulang. Jangan pakai
  pola cerita kegagalan kalau jurnal tidak menyebut kegagalan.
- Hook dan alasan TIDAK BOLEH mengklaim kejadian, angka, kesalahan, atau rahasia yang tidak
  disebut di jurnal. Kalau jurnal tipis, buat hook yang jujur dan sempit, bukan dilebih-lebihkan.
- Nama proyek yang benar: Talatee. Pakai ejaan benar di hook dan alasan; kutipan tetap
  disalin persis dari jurnal.
- Jangan mengulang hook dari 7 hari terakhir (daftar diberikan).
- "kutipan" WAJIB disalin persis dari jurnal (3 sampai 20 kata), tanpa diubah.
- Jangan menambah fakta yang tidak ada di jurnal.

Format balasan (JSON saja, tanpa teks lain):
{"hooks":[{"hook":"kalimat pembuka, maks 15 kata","pola":"nama pola",
"alasan":"2 kalimat: kenapa orang berhenti scroll dan kenapa relevan untuk audiens Ashar",
"kutipan":"potongan persis dari jurnal","format":"Reels / thread / carousel / screen recording"}]}"""


class HookGenerationError(Exception):
    pass


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def call_hermes(messages: list[dict]) -> str:
    if not settings.hermes_api_key:
        raise HookGenerationError("HERMES_API_KEY belum di-set.")
    try:
        with httpx.Client(timeout=300) as client:
            resp = client.post(
                f"{settings.hermes_api_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.hermes_api_key}"},
                json={"model": "hermes-agent", "messages": messages, "stream": False},
            )
            resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except httpx.HTTPError as exc:
        raise HookGenerationError(f"Hermes tidak terjangkau/error ({type(exc).__name__}).") from exc
    except (KeyError, IndexError, ValueError) as exc:
        raise HookGenerationError("Format balasan Hermes tidak dikenali.") from exc


def parse_hooks(raw: str) -> list[dict]:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return []
    try:
        data = json.loads(raw[start : end + 1])
    except ValueError:
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    return [h for h in hooks if isinstance(h, dict)] if isinstance(hooks, list) else []


def validate_hooks(candidates: list[dict], transcript: str) -> tuple[list[dict], list[dict]]:
    """Kembalikan (lolos, ditolak). Lolos = semua field terisi dan kutipan ada di jurnal."""
    base = _norm(transcript)
    good, bad = [], []
    for h in candidates:
        if not all(isinstance(h.get(k), str) and h[k].strip() for k in FIELDS):
            bad.append(h)
            continue
        clean = {k: h[k].strip() for k in FIELDS}
        q = _norm(clean["kutipan"])
        if len(q.split()) < 3 or q not in base or len(clean["hook"].split()) > 25:
            bad.append(h)
            continue
        good.append(clean)
    return good, bad


def _user_prompt(transcript: str, history: list[str]) -> str:
    hist = "\n".join(f"- {h}" for h in history) if history else "(belum ada)"
    return f"HOOK 7 HARI TERAKHIR (jangan diulang):\n{hist}\n\nJURNAL HARI INI:\n{transcript}"


def generate_hooks(transcript: str, history: list[str], ask=call_hermes) -> list[dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_prompt(transcript, history)},
    ]
    valid: list[dict] = []
    seen: set[str] = set()
    for _ in range(2):
        raw = ask(messages)
        if "{" not in raw:  # bukan JSON: biasanya pesan error dari model/penyedia Hermes
            snippet = " ".join(raw.split())[:300]
            raise HookGenerationError(f"Hermes tidak mengembalikan hook: {snippet}")
        good, bad = validate_hooks(parse_hooks(raw), transcript)
        for h in good:
            key = _norm(h["hook"])
            if key not in seen:
                seen.add(key)
                valid.append(h)
        if len(valid) >= MIN_HOOKS:
            return valid[:MIN_HOOKS]
        messages = messages + [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": (
                    f"Baru {len(valid)} hook yang lolos. {len(bad)} ditolak karena field kurang atau "
                    "kutipan tidak ada persis di jurnal. Buat ulang 5 hook penuh; salin kutipan persis "
                    "dari jurnal. Balas JSON saja."
                ),
            },
        ]
    raise HookGenerationError(f"Hanya {len(valid)} hook valid dari {MIN_HOOKS} yang dibutuhkan.")


def format_messages(hooks: list[dict], when: datetime) -> list[str]:
    """Pesan Telegram (teks polos). Jurnal mentah TIDAK ikut dikirim, hanya hook + kutipan pendek."""
    hari = HARI[when.astimezone(WIB).weekday()]
    parts = [f"🎙 Jurnal {hari} → {len(hooks)} hook untukmu"]
    for i, h in enumerate(hooks, 1):
        alasan = h["alasan"] if len(h["alasan"]) <= 400 else h["alasan"][:397] + "..."
        parts.append(
            f"{i}. “{h['hook']}”\n"
            f"Pola: {h['pola']} · Format: {h['format']}\n"
            f"Kenapa kuat: {alasan}\n"
            f"Sumber: “{h['kutipan']}”"
        )
    parts.append("Detail lengkap dan riwayat hook ada di Kompas.")
    messages, cur = [], parts[0]
    for block in parts[1:]:
        if len(cur) + 2 + len(block) > TELEGRAM_CHUNK:
            messages.append(cur)
            cur = block
        else:
            cur += "\n\n" + block
    messages.append(cur)
    return messages
