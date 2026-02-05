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

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(store.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
