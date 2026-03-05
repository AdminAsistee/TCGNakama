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

_showcase_task = None
_SHOWCASE_INTERVAL_DAYS = 3
_SHOWCASE_CARD_LIMIT = 3  # how many Fresh Pulls to pick per run


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
            print("[BLOG] Generating new article...", flush=True)
            db = SessionLocal()
            try:
                post = await generate_article(db)
                if post:
                    print(f"[BLOG] Published: '{post.title}'", flush=True)
                else:
                    print("[BLOG] generate_article returned None (duplicate or API error)", flush=True)
            finally:
                db.close()

        except asyncio.CancelledError:
            print("[BLOG] Blog scheduler cancelled", flush=True)
            break
        except Exception as e:
            import traceback
            print(f"[BLOG ERROR] {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            await asyncio.sleep(60 * 10)  # back-off 10 min on error


# ─────────────────────────────────────────────────────────────────────────────
# Showcase Video Scheduler
# Generates a New Cards Showcase video every 3 days using Fresh Pulls.
# Skips the run if the top-N cards haven't changed since the last video.
# ─────────────────────────────────────────────────────────────────────────────
async def _showcase_loop():
    """Background loop: generate a showcase video every 3 days if cards changed."""
    import logging, json, os, sys
    logger = logging.getLogger(__name__)  # define logger for the whole function
    print("[SHOWCASE] Scheduler started", flush=True)

    while True:
        try:
            # ── Wait until next window ──────────────────────────────────────
            now = _dt.now(_tz.utc)

            # Try to read last_run from GCS to know when we last ran
            last_run_at = None
            last_card_ids: list = []
            try:
                from google.cloud import storage as _gcs_storage
                import os as _os
                _project  = _os.getenv("GCP_PROJECT_ID", "tcgnakama")
                _bucket   = _os.getenv("GCS_BUCKET", "ready-bucket")
                _gcs      = _gcs_storage.Client(project=_project)
                _blob     = _gcs.bucket(_bucket).blob("showcase/last_run.json")
                if _blob.exists():
                    raw = json.loads(_blob.download_as_text())
                    last_run_at   = _dt.fromisoformat(raw["run_at"])
                    last_card_ids = raw.get("card_ids", [])
                    print(f"[SHOWCASE] Last run: {last_run_at.isoformat()} | {len(last_card_ids)} cards", flush=True)
            except Exception as e:
                print(f"[SHOWCASE] Could not load last_run.json: {e}", flush=True)

            # Decide when next run should happen.
            # IMPORTANT: only honour a previous run if it actually processed cards.
            # An empty card_ids list means the pipeline aborted (0 in-stock cards).
            # Treat that as "no valid prior run" but schedule 3 days from now to
            # avoid the 30-second infinite-loop when no cards are ever in stock.
            if last_run_at and last_card_ids:
                # Normal case: wait until 3 days after the last successful run
                next_run = last_run_at + _td(days=_SHOWCASE_INTERVAL_DAYS)
            elif last_run_at and not last_card_ids:
                # Previous run had 0 cards (aborted). Wait 3 days from that run_at
                # rather than re-triggering in 30 s — avoids the infinite loop.
                next_run = last_run_at + _td(days=_SHOWCASE_INTERVAL_DAYS)
                print("[SHOWCASE] Last run had 0 cards — waiting 3 days before retry", flush=True)
            else:
                next_run = now + _td(seconds=30)  # no last_run.json at all — start soon

            wait_seconds = (next_run - now).total_seconds()
            if wait_seconds > 0:
                print(f"[SHOWCASE] Next run in {wait_seconds/3600:.1f}h ({wait_seconds:.0f}s)", flush=True)
                await asyncio.sleep(wait_seconds)

            # ── Time to run — check if cards changed ────────────────────────
            print("[SHOWCASE] Checking Fresh Pulls...", flush=True)
            try:
                client = ShopifyClient()
                products = await client.get_products()
                in_stock = [p for p in products if p.get('totalInventory', 0) > 0]
                fresh = sorted(in_stock, key=lambda x: x.get('createdAt', ''), reverse=True)
                candidates = fresh[:_SHOWCASE_CARD_LIMIT]
                candidate_ids = [p['id'] for p in candidates]
            except Exception as e:
                print(f"[SHOWCASE] Shopify fetch failed: {e}", flush=True)
                await asyncio.sleep(60 * 30)  # retry in 30 min
                continue

            if set(candidate_ids) == set(last_card_ids) and last_card_ids:
                print(
                    f"[SHOWCASE] Cards unchanged since last run — skipping video generation.\n"
                    f"  Same cards: {[p['title'][:30] for p in candidates]}",
                    flush=True
                )
                # Bump last_run_at so we wait another 3 days before checking again
                try:
                    bump = {"run_at": _dt.now(_tz.utc).isoformat(), "card_ids": last_card_ids}
                    _gcs.bucket(_bucket).blob("showcase/last_run.json").upload_from_string(
                        json.dumps(bump), content_type="application/json"
                    )
                except Exception:
                    pass
                continue

            # ── Cards changed — kick off the full pipeline ──────────────────
            print("[SHOWCASE] New cards detected — starting video pipeline...", flush=True)
            try:
                # Import and run the main showcase pipeline
                sys.path.insert(0, '.')
                import importlib
                showcase = importlib.import_module("test_flywheel_video")
                # Run in a thread so it doesn't block the event loop
                # (ffmpeg + Pollo polls are blocking/synchronous)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: asyncio.run(showcase.main()))
                print("[SHOWCASE] Pipeline complete.", flush=True)
            except Exception as e:
                import traceback
                print(f"[SHOWCASE] Pipeline failed: {e}", flush=True)
                print(traceback.format_exc(), flush=True)
                await asyncio.sleep(60 * 10)  # back-off 10 min

        except asyncio.CancelledError:
            print("[SHOWCASE] Showcase scheduler cancelled", flush=True)
            break
        except Exception as e:
            import traceback
            print(f"[SHOWCASE ERROR] {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            await asyncio.sleep(60 * 10)


def start_background_tasks():
    """Start all background tasks."""
    global _polling_task, _blog_task, _showcase_task

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

    if _showcase_task is None:
        _showcase_task = asyncio.create_task(_showcase_loop())
        print("[BACKGROUND] Showcase video scheduler started")
    else:
        print("[BACKGROUND] Showcase video scheduler already running")


async def stop_background_tasks():
    """Stop all background tasks."""
    global _polling_task, _blog_task, _showcase_task

    for task, name in [(_polling_task, "polling"), (_blog_task, "blog"), (_showcase_task, "showcase")]:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            print(f"[BACKGROUND] {name} task stopped")

    _polling_task = None
    _blog_task = None
    _showcase_task = None
