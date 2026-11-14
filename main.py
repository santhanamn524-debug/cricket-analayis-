"""
backend/main.py
===============
RR Intelligence Hub – FastAPI Application Server
Provides unified REST APIs and static file delivery for the frontend dashboard.
"""

import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.routes import health, players, rankings, predictions, intelligence, system, training
from database.connection import Base, engine, SQLITE_PATH
from database.loader import run_loader

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("rr_hub_server")

app = FastAPI(
    title="RR Intelligence Hub API",
    description="Professional Cricket Intelligence Platform for Rajasthan Royals Recruitment & Match Analytics",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health.router, prefix="/api")
app.include_router(players.router, prefix="/api")
app.include_router(rankings.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(training.router, prefix="/api")

# Static frontend mounts
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


@app.on_event("startup")
def on_startup():
    log.info("Starting RR Intelligence Hub...")
    # Verify database exists or initialize it
    if not SQLITE_PATH.exists():
        log.info("Database not found. Triggering automated ingestion and setup...")
        run_loader()
    log.info("RR Intelligence Hub API is READY to serve requests.")


@app.get("/")
def serve_index():
    """Serve the single-page dashboard application."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "RR Intelligence Hub API is running. Frontend index.html loading..."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
