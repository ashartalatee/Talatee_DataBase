"""
Entrypoint FastAPI. Jalankan dengan:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, batches, businesses, core, datasets, health, ingestion, lab_entries, projects, sources, stats

app = FastAPI(title="Talatee Personal Big Data Platform", version="0.1.0")

# Dashboard React (Phase 2) jalan di port dev server terpisah (default Vite: 5173),
# jadi perlu CORS supaya browser mengizinkan pemanggilan API dari origin lain.
# Platform ini untuk pemakaian pribadi/lokal, jadi origin localhost dibuka semua.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
app.include_router(projects.router)
app.include_router(lab_entries.router)
app.include_router(batches.router)
app.include_router(stats.router)
