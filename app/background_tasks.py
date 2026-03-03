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
_cached_products = []     # In-memory product cache — populated every 30 min
_cached_collections = []  # In-memory collections cache — populated every 30 min


def get_cached_products() -> list:
    """Return the in-memory product cache (populated by background sync)."""
    return _cached_products


def get_cached_collections() -> list:
    """Return the in-memory collections cache (populated by background sync)."""
    return _cached_collections


async def sync_shopify_products():
    """Fetch latest products AND collections from Shopify and cache both."""
    global _last_sync_time, _sync_in_progress, _cached_products, _cached_collections

    if _sync_in_progress:
        print("[SYNC] Sync already in progress, skipping...")
        return

    try:
        _sync_in_progress = True
        print(f"[SYNC] Starting Shopify sync at {datetime.now()}")

        client = ShopifyClient()
        # Fetch products and collections in parallel — saves ~1s vs sequential
        products, collections = await asyncio.gather(
            client.get_products(),
            client.get_collections()
        )

        _cached_products = products
        _cached_collections = collections
        _last_sync_time = datetime.now()
        print(f"[SYNC] Cached {len(products)} products + {len(collections)} collections at {_last_sync_time}")

    except Exception as e:
        print(f"[SYNC ERROR] Failed to sync: {e}")
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
