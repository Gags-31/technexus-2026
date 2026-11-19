"""TECHNEXUS 2026 - synchronised technical quiz platform API."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import SessionLocal, init_db
from .realtime import websocket_endpoint
from .routers import admin_competition, admin_core, auth, participant, registration
from .seed import seed_all
from .services.core import settings_map
from .services.rounds import check_auto_end

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# Local development serves frontend/dist. On Vercel the built frontend is bundled
# with the backend function so a single deployment serves both UI and API.
FRONTEND_DIST = next(
    (
        candidate
        for candidate in (
            PROJECT_ROOT / "backend" / "frontend_dist",
            PROJECT_ROOT / "frontend" / "dist",
        )
        if (candidate / "index.html").exists()
    ),
    PROJECT_ROOT / "frontend" / "dist",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seeded = seed_all(db)
        print(f"[TECHNEXUS] seeded {seeded['questions']} questions, "
              f"{seeded['riddles']} riddles, {seeded['memes']} memes")
    finally:
        db.close()

    async def round_clock() -> None:
        while True:
            await asyncio.sleep(3)
            try:
                db2 = SessionLocal()
                try:
                    ended = check_auto_end(db2)
                finally:
                    db2.close()
                from .realtime import hub
                for round_id in ended:
                    await hub.broadcast("round.ended", {
                        "round_id": round_id,
                        "message": "Time is up. Saved answers were submitted automatically.",
                    }, channel="participant")
                    await hub.broadcast("scoreboard.updated", {"round_id": round_id}, channel="administrator")
                    await hub.broadcast("round.changed", {}, channel="administrator")
            except Exception as exc:  # keep the scheduler alive
                print(f"[TECHNEXUS] clock error: {exc}")

    task = asyncio.create_task(round_clock())
    yield
    task.cancel()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AWS Student Builder Group - CONNECT. THINK. CONQUER.",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces or answer data to clients.
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
def health():
    return {"ok": True, "service": "TECHNEXUS 2026", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/time")
def server_time():
    return {"now": datetime.now(timezone.utc).isoformat()}


@app.get("/api/public/config")
def public_config():
    db = SessionLocal()
    try:
        cfg = settings_map(db)
        return {
            "event_name": "TECHNEXUS 2026",
            "tagline": "CONNECT. THINK. CONQUER.",
            "subtitle": "THE ULTIMATE TECH QUIZ",
            "organiser": "AWS Student Builder Group (AWSSBG)",
            "event_date": cfg.get("event_date"),
            "event_start_time": cfg.get("event_start_time"),
            "schedule": cfg.get("schedule", []),
            "domains": ["Artificial Intelligence", "Cloud Computing", "Operating Systems", "DBMS"],
            "rounds": [
                {"id": 1, "name": "TECH BLITZ", "duration": 25},
                {"id": 2, "name": "DECODE THE DOMAIN", "duration": 25},
                {"id": 3, "name": "TECH TROUBLESHOOTER", "duration": 35},
                {"id": 4, "name": "NEXUS SHOWDOWN", "duration": 30},
            ],
            "team_size": 2,
            "logo": "/assets/awssbg-logo.png",
        }
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(registration.router)
app.include_router(participant.router)
app.include_router(admin_core.router)
app.include_router(admin_competition.router)

app.add_api_websocket_route("/ws", websocket_endpoint)

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if full_path.startswith("api/") or full_path == "ws":
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(status_code=404, content={"detail": "Frontend build not found. Run npm run build in frontend/."})
