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


# ─────────────────────────────────────────────────────────────────────────────
# Blog Auto-Publishing Scheduler
# Publishes a new AI-generated article every 3 days at a random time 08-20 JST
# ─────────────────────────────────────────────────────────────────────────────
import random as _random
from datetime import datetime as _dt, timezone as _tz, timedelta as _td

_blog_task = None
_BLOG_INTERVAL_DAYS = 3


async def _blog_loop():
    """Background loop: generate + publish a blog post every 3 days."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[BLOG] Blog scheduler started")

    from app.database import SessionLocal
    from app.models import BlogPost
    from app.services.blog_generator import generate_article

    while True:
        try:
            db = SessionLocal()
            try:
                # Find the most recent published post
                last_post = (
                    db.query(BlogPost)
                    .filter(BlogPost.is_published == True)
                    .order_by(BlogPost.published_at.desc())
                    .first()
                )
            finally:
                db.close()

            now = _dt.now(_tz.utc)

            if last_post and last_post.published_at:
                # Make published_at timezone-aware if it isn't
                last_pub = last_post.published_at
                if last_pub.tzinfo is None:
                    last_pub = last_pub.replace(tzinfo=_tz.utc)
                next_publish = last_pub + _td(days=_BLOG_INTERVAL_DAYS)
            else:
                # No posts yet — generate one after a 10-second startup delay
                next_publish = now + _td(seconds=10)

            # Add random offset: 0-12 hours within the publish day (for "random time")
            random_offset_hours = _random.uniform(0, 12)
            next_publish = next_publish + _td(hours=random_offset_hours)

            wait_seconds = (next_publish - now).total_seconds()
            if wait_seconds < 0:
                wait_seconds = 5  # overdue — publish soon

            logger.info(f"[BLOG] Next article in {wait_seconds/3600:.1f}h (at {next_publish.isoformat()})")
            await asyncio.sleep(max(wait_seconds, 5))

            # Generate & publish
            logger.info("[BLOG] Generating new article...")
            db = SessionLocal()
            try:
                post = await generate_article(db)
                if post:
                    fb_id = await post_to_facebook_group(post)
                    if fb_id:
                        post.facebook_post_id = fb_id
                        db.commit()
            finally:
                db.close()

        except asyncio.CancelledError:
            logger.info("[BLOG] Blog scheduler cancelled")
            break
        except Exception as e:
            import logging as _log
            _log.getLogger(__name__).error(f"[BLOG ERROR] {e}")
            await asyncio.sleep(60 * 10)  # back-off 10 min on error


def start_background_tasks():
    """Start all background tasks."""
    global _polling_task, _blog_task

    if _polling_task is None:
        _polling_task = asyncio.create_task(polling_task())
        print("[BACKGROUND] Shopify polling task started")
    else:
        print("[BACKGROUND] Shopify polling task already running")

    if _blog_task is None:
        _blog_task = asyncio.create_task(_blog_loop())
        print("[BACKGROUND] Blog scheduler task started")
    else:
        print("[BACKGROUND] Blog scheduler task already running")


async def stop_background_tasks():
    """Stop all background tasks."""
    global _polling_task, _blog_task

    for task, name in [(_polling_task, "polling"), (_blog_task, "blog")]:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            print(f"[BACKGROUND] {name} task stopped")

    _polling_task = None
    _blog_task = None
