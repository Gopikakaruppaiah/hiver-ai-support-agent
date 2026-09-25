import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.api.routes import router

app = FastAPI(
    title="Hiver AI Support Agent — Uber_Support",
    description="Intent classification, historically-grounded reply generation, "
                "and auto-handle/escalate decisioning for Uber_Support (ride-hailing scope).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:4173", "http://127.0.0.1:4173",  # vite preview
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
