"""
Meneruskan chat dari dashboard ke Hermes -- lewat API server OpenAI-compatible
Hermes (default port 8642), BUKAN port dashboard 9119 yang selama ini dipakai
buat browser (127.0.0.1:9119/chat). Dua layanan itu terpisah di Hermes sendiri.

Sebelum endpoint ini bisa jalan, API server Hermes harus diaktifkan dulu
(lewat menu Channels di dashboard Hermes, atau ~/.hermes/.env:
API_SERVER_ENABLED=true, API_SERVER_KEY=<sesuatu>), dan nilai yang sama
diisi ke HERMES_API_KEY di .env Talatee ini.

Stateless: seluruh riwayat percakapan dikirim ulang tiap request (format
persis OpenAI chat completions) -- FastAPI ini sendiri tidak menyimpan sesi,
histori disimpan di sisi dashboard (localStorage/state React) dan dikirim
balik tiap kali kirim pesan baru.
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    if not settings.hermes_api_key:
        raise HTTPException(
            status_code=500,
            detail="HERMES_API_KEY belum di-set di .env -- lihat komentar di atas file ini.",
        )

    messages = [{"role": m.role, "content": m.content} for m in payload.history]
    messages.append({"role": "user", "content": payload.message})

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{settings.hermes_api_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.hermes_api_key}"},
                json={"model": "hermes-agent", "messages": messages, "stream": False},
            )
            resp.raise_for_status()
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Tidak bisa terhubung ke Hermes API server di {settings.hermes_api_url}. "
                "Pastikan API server Hermes aktif (menu Channels) dan gateway-nya jalan."
            ),
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                "Hermes tidak membalas dalam 300 detik (mungkin sedang mikir panjang atau "
                "manggil banyak tool). Coba lagi, atau perpendek pertanyaannya."
            ),
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Hermes API server membalas error: {exc.response.status_code} {exc.response.text}",
        ) from exc
    except httpx.HTTPError as exc:
        # Payung terakhir untuk error httpx lain yang belum ditangani secara
        # spesifik di atas (mis. koneksi putus di tengah jalan) -- supaya
        # dashboard selalu dapat pesan error yang jelas, bukan "Failed to
        # fetch" mentah dari browser.
        raise HTTPException(
            status_code=502, detail=f"Gagal menghubungi Hermes API server: {exc}"
        ) from exc

    data = resp.json()
    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=502, detail=f"Format balasan Hermes tidak dikenali: {data}"
        ) from exc

    return ChatResponse(reply=reply)
