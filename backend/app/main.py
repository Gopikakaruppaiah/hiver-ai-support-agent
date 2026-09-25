import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

_FRONTEND_DIST = _REPO_ROOT / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        requested_file = _FRONTEND_DIST / full_path

        if full_path and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(_FRONTEND_DIST / "index.html")