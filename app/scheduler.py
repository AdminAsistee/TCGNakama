"""
APScheduler integration for TCG Nakama.
Manages scheduled price updates based on admin settings.
"""
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models import SystemSetting

logger = logging.getLogger("scheduler")

# Module-level scheduler instance
_scheduler: AsyncIOScheduler | None = None
_batch_running = False

# Frequency → cron mapping (all run at 3:00 AM JST)
FREQUENCY_CRON = {
    "daily":       CronTrigger(hour=3, minute=0, timezone="Asia/Tokyo"),
    "every_3_days": CronTrigger(day="*/3", hour=3, minute=0, timezone="Asia/Tokyo"),
    "weekly":      CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="Asia/Tokyo"),
}

JOB_ID = "price_batch_update"


def _get_setting(key: str, default: str = "") -> str:
    """Read a SystemSetting value."""
    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter_by(key=key).first()
        return row.value if row else default
    finally:
        db.close()


def _set_setting(key: str, value: str):
    """Write a SystemSetting value."""
    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key=key, value=value))
        db.commit()
    finally:
        db.close()


async def _run_batch_job():
    """Scheduled job: fetch products & run batch price update."""
    global _batch_running
    if _batch_running:
        logger.warning("Batch already running, skipping this trigger")
        return

    _batch_running = True
    _set_setting("price_tracker_status", "running")
    logger.info("=== Scheduled price batch starting ===")

    try:
        # Import here to avoid circular imports
        from app.dependencies import get_shopify_client
        from app.services.price_tracker import run_batch_update

        client = get_shopify_client()
        products = await client.get_products()

        if not products:
            logger.warning("No products from Shopify, skipping batch")
            _set_setting("price_tracker_status", "idle")
            _batch_running = False
            return

        result = await run_batch_update(products)
        logger.info(f"Batch result: {result}")
        _set_setting("price_tracker_status", "idle")

    except Exception as e:
        logger.error(f"Batch job failed: {e}", exc_info=True)
        _set_setting("price_tracker_status", "failed")
        _set_setting("price_tracker_last_error", str(e)[:500])
    finally:
        _batch_running = False


def get_scheduler() -> AsyncIOScheduler | None:
    """Return the module-level scheduler instance."""
    return _scheduler


def is_batch_running() -> bool:
    """Check if a batch job is currently running."""
    return _batch_running


def start_scheduler():
    """Initialize and start the APScheduler."""
    global _scheduler

    _scheduler = AsyncIOScheduler()

    # Read saved frequency or default to weekly
    frequency = _get_setting("price_update_frequency", "weekly")
    trigger = FREQUENCY_CRON.get(frequency, FREQUENCY_CRON["weekly"])

    _scheduler.add_job(
        _run_batch_job,
        trigger=trigger,
        id=JOB_ID,
        replace_existing=True,
        name="PriceCharting batch update",
    )

    _scheduler.start()
    logger.info(f"Scheduler started (frequency={frequency})")


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
        _scheduler = None


def reschedule(frequency: str):
    """
    Update the batch job schedule (called when admin changes frequency).
    
    Args:
        frequency: One of 'daily', 'every_3_days', 'weekly'
    """
    global _scheduler
    if not _scheduler:
        logger.warning("Scheduler not running, cannot reschedule")
        return

    trigger = FREQUENCY_CRON.get(frequency)
    if not trigger:
        logger.error(f"Unknown frequency: {frequency}")
        return

    _scheduler.reschedule_job(JOB_ID, trigger=trigger)
    _set_setting("price_update_frequency", frequency)
    logger.info(f"Rescheduled to: {frequency}")


async def trigger_manual_run():
    """Trigger an immediate batch run (from admin panel 'Run Now' button)."""
    if _batch_running:
        return {"status": "already_running"}

    # Run in background so the HTTP response returns immediately
    asyncio.create_task(_run_batch_job())
    return {"status": "started"}
