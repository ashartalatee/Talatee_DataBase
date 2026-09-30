"""
Entrypoint FastAPI. Jalankan dengan:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, batches, businesses, chat, core, data_trust, datasets, health, ingestion, lab_entries, projects, sources, stats, trash

app = FastAPI(title="Talatee Personal Big Data Platform", version="0.1.0")

# Dashboard React (Phase 2) jalan di port dev server terpisah (default Vite: 5173),
# jadi perlu CORS supaya browser mengizinkan pemanggilan API dari origin lain.
# Platform ini untuk pemakaian pribadi/lokal, jadi origin localhost dibuka semua.
#
# allow_origin_regex tambahan untuk VS Code port forwarding (devtunnels) —
# URL-nya berbentuk https://<id>-<port>.<region>.devtunnels.ms, beda tiap
# sesi forwarding jadi tidak bisa didaftar satu-satu di allow_origins. Kalau
# nanti pakai layanan tunnel lain (ngrok, dst), tambahkan pattern-nya di sini
# juga -- jangan pernah pakai allow_origins=["*"] bareng allow_credentials=True,
# browser akan menolak kombinasi itu untuk request yang bawa cookie/session.
# allow_origin_regex tambahan untuk:
# 1. VS Code port forwarding (devtunnels) -- https://<id>-<port>.<region>.devtunnels.ms
# 2. Tailscale -- IP CGNAT (100.x.x.x, rentang khusus Tailscale) ATAU
#    MagicDNS (*.ts.net) -- keduanya cuma bisa diakses dari perangkat yang
#    sudah gabung tailnet pribadi Anda, jadi aman dibuka lebih longgar
#    dibanding origin publik biasa.
# 3. Vercel -- domain production dashboard (tetap) didaftar eksplisit di
#    allow_origins, sedangkan URL preview (talatee-dashboard-<hash>.vercel.app,
#    beda tiap deploy) dicakup lewat regex supaya tidak perlu update manual
#    setiap kali ada deployment baru.
# Jangan pernah pakai allow_origins=["*"] bareng allow_credentials=True,
# browser akan menolak kombinasi itu untuk request yang bawa cookie/session.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://talatee-dashboard.vercel.app",
    ],
    allow_origin_regex=r"^https?://(.*\.devtunnels\.ms|100\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?|.*\.ts\.net(:\d+)?|talatee-dashboard-.*\.vercel\.app)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(ingestion.router)
app.include_router(businesses.router)
app.include_router(sources.router)
app.include_router(datasets.router)
app.include_router(core.router)
app.include_router(data_trust.router)
app.include_router(projects.router)
app.include_router(lab_entries.router)
app.include_router(batches.router)
app.include_router(stats.router)
app.include_router(trash.router)
app.include_router(chat.router)
from app.api.routes import kompas
app.include_router(kompas.router)
from app.api.routes import kompas_ideas
app.include_router(kompas_ideas.router)