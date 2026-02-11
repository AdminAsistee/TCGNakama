"""
Background tasks for TCG Nakama.
Handles periodic syncing with Shopify and other scheduled operations.
"""
import asyncio
from datetime import datetime
from app.dependencies import ShopifyClient

# Global state for background tasks
_polling_task = None
_last_sync_time = None
_sync_in_progress = False


async def sync_shopify_products():
    """Fetch latest products from Shopify and cache them."""
    global _last_sync_time, _sync_in_progress
    
    if _sync_in_progress:
        print("[SYNC] Sync already in progress, skipping...")
        return
    
    try:
        _sync_in_progress = True
        print(f"[SYNC] Starting Shopify product sync at {datetime.now()}")
        
        client = ShopifyClient()
        products = await client.get_products()
        
        _last_sync_time = datetime.now()
        print(f"[SYNC] Successfully synced {len(products)} products at {_last_sync_time}")
        
    except Exception as e:
        print(f"[SYNC ERROR] Failed to sync products: {e}")
    finally:
        _sync_in_progress = False


async def polling_task():
    """Background task that polls Shopify every 30 minutes."""
    print("[POLLING] Background polling task started")
    
    # Initial sync on startup
    await sync_shopify_products()
    
    # Poll every 30 minutes
    while True:
        try:
            await asyncio.sleep(30 * 60)  # 30 minutes in seconds
            await sync_shopify_products()
        except asyncio.CancelledError:
            print("[POLLING] Polling task cancelled")
            break
        except Exception as e:
            print(f"[POLLING ERROR] Error in polling task: {e}")
            # Continue polling even if there's an error
            await asyncio.sleep(60)  # Wait 1 minute before retrying


def start_background_tasks():
    """Start all background tasks."""
    global _polling_task
    
    if _polling_task is None:
        _polling_task = asyncio.create_task(polling_task())
        print("[BACKGROUND] Background tasks started")
    else:
        print("[BACKGROUND] Background tasks already running")


async def stop_background_tasks():
    """Stop all background tasks."""
    global _polling_task
    
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        _polling_task = None
        print("[BACKGROUND] Background tasks stopped")


def get_sync_status():
    """Get current sync status."""
    return {
        "last_sync": _last_sync_time.isoformat() if _last_sync_time else None,
        "sync_in_progress": _sync_in_progress
    }
