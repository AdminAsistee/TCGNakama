from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import store
import os
import asyncio
from app.dependencies import get_shopify_client

app = FastAPI(title="TCG Nakama")

# Background Polling Task
async def poll_shopify_vault():
    client = get_shopify_client()
    while True:
        try:
            print("\n[PULSE] Shopify Vault Sync: Initiating Heartbeat...")
            products = await client.get_products()
            print(f"[PULSE] Shopify Vault Sync: SUCCESS ({len(products)} units verified)")
        except Exception as e:
            print(f"[PULSE] Shopify Vault Sync: ERROR - {e}")
        
        # Wait 10 minutes
        await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(poll_shopify_vault())
    
    # Email report scheduler (DISABLED - enable when ready)
    # from app.scheduler import start_scheduler
    # start_scheduler()
    # print("[STARTUP] Daily email report scheduler initialized")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
