from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import store
import os
import asyncio
from dotenv import load_dotenv
from app.dependencies import get_shopify_client
from app.background_tasks import start_background_tasks, stop_background_tasks, get_sync_status

load_dotenv(override=True)

app = FastAPI(title="TCG Nakama")

@app.on_event("startup")
async def startup_event():
    # Initialize database
    from app.database import init_db, SessionLocal
    from app.models import Banner
    
    init_db()
    print("[STARTUP] Database tables initialized")
    
    # Seed default banners if none exist
    db = SessionLocal()
    try:
        banner_count = db.query(Banner).count()
        if banner_count == 0:
            print("[STARTUP] Seeding default banners...")
            default_banners = [
                Banner(
                    title="One Piece: Four Emperors",
                    subtitle="The ultimate pirate cards have arrived",
                    cta_label="Shop One Piece",
                    cta_link="/",
                    gradient="from-red-900 via-orange-900 to-amber-900",
                    image_path=None,
                    display_order=1,
                    is_active=True
                ),
                Banner(
                    title="Pokémon Scarlet & Violet",
                    subtitle="Explore the latest expansion — chase the illustrators",
                    cta_label="Shop Pokémon",
                    cta_link="/",
                    gradient="from-violet-900 via-purple-900 to-indigo-900",
                    image_path=None,
                    display_order=2,
                    is_active=True
                ),
                Banner(
                    title="One Piece: Romance Dawn",
                    subtitle="Where the legend began — Romance Dawn collection",
                    cta_label="Shop Romance Dawn",
                    cta_link="/",
                    gradient="from-sky-900 via-cyan-900 to-teal-900",
                    image_path=None,
                    display_order=3,
                    is_active=True
                ),
            ]
            db.add_all(default_banners)
            db.commit()
            print(f"[STARTUP] Seeded {len(default_banners)} default banners")
    finally:
        db.close()
    
    # Start background Shopify sync (30-minute polling)
    start_background_tasks()
    
    # Email report scheduler (DISABLED - enable when ready)
    # from app.scheduler import start_scheduler
    # start_scheduler()
    # print("[STARTUP] Daily email report scheduler initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of background tasks."""
    await stop_background_tasks()
    print("[SHUTDOWN] Application shutdown complete")

# Mount static files with absolute path
from pathlib import Path
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
# Include routers
app.include_router(store.router)

from app.routers import admin
app.include_router(admin.router, prefix="/admin", tags=["admin"])

from app.routers import oauth
app.include_router(oauth.router, tags=["oauth"])

# Search tracking endpoint
from fastapi import HTTPException
from pydantic import BaseModel
from app import cost_db

class SearchTrack(BaseModel):
    query: str
    results_count: int = 0

@app.post("/api/track-search")
async def track_search(data: SearchTrack):
    """Log a search query for analytics."""
    if not data.query or len(data.query.strip()) < 2:
        return {"success": False, "error": "Query too short"}
    
    try:
        cost_db.log_search(data.query, data.results_count)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Manual report trigger (for testing)
@app.post("/api/trigger-report")
async def trigger_report():
    """Manually trigger a daily report email (for testing)."""
    from app.scheduler import trigger_report_now
    await trigger_report_now()
    return {"success": True, "message": "Report triggered - check console/email"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
