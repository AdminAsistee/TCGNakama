"""
Scheduler Service for TCG Nakama
Handles scheduled tasks like daily email reports using APScheduler.
"""

import os
import asyncio
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.email_service import send_email, generate_daily_report_html
from app import cost_db


# Global scheduler instance
scheduler = None


async def collect_report_data() -> dict:
    """Collect analytics data for the daily report."""
    from app.dependencies import get_shopify_client
    from app.routers.admin import fetch_shopify_orders, analyze_top_spenders
    
    client = get_shopify_client()
    
    try:
        products = await client.get_products()
    except Exception:
        products = []
    
    try:
        orders = await fetch_shopify_orders(limit=50)
    except Exception:
        orders = []
    
    # Get grades from local DB
    all_grades = cost_db.get_all_grades()
    total_graded = len([g for g in all_grades.values() if g])
    
    # Get trending searches
    trending_searches = cost_db.get_trending_searches(days=30, limit=5)
    
    # Calculate top spenders
    top_spenders = analyze_top_spenders(orders)
    
    # Calculate PSA 10 candidates (simple version)
    psa_candidates = []
    for product in products:
        product_id = product.get('id', '')
        grade = all_grades.get(product_id)
        if grade in ['S', 'A']:
            score = 80 if grade == 'S' else 60
            price = float(product.get('price', 0))
            if price > 5000:
                score += 15
            psa_candidates.append({
                'title': product.get('title', 'Unknown')[:40],
                'grade': grade,
                'score': min(score, 100)
            })
    
    psa_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Build top products list (by price)
    top_products = sorted(products, key=lambda x: float(x.get('price', 0)), reverse=True)[:5]
    top_products = [{'title': p.get('title', '')[:40], 'price': float(p.get('price', 0))} for p in top_products]
    
    return {
        'total_products': len(products),
        'total_orders': len(orders),
        'total_graded': total_graded,
        'top_products': top_products,
        'top_spenders': top_spenders,
        'trending_searches': trending_searches,
        'psa_candidates': psa_candidates[:3]
    }


async def send_daily_report():
    """Send the daily analytics report email."""
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)
    print(f"[SCHEDULER] Running daily report at {now.strftime('%Y-%m-%d %H:%M:%S')} JST")
    
    try:
        data = await collect_report_data()
        html_content = generate_daily_report_html(data)
        subject = f"📊 TCG Nakama Daily Report - {now.strftime('%Y/%m/%d')}"
        
        success = send_email(subject, html_content)
        if success:
            print("[SCHEDULER] Daily report sent successfully!")
        else:
            print("[SCHEDULER] Daily report failed to send (check SMTP config)")
    except Exception as e:
        print(f"[SCHEDULER] Error generating daily report: {e}")


def init_scheduler():
    """Initialize the APScheduler with scheduled jobs."""
    global scheduler
    
    if scheduler is not None:
        print("[SCHEDULER] Already initialized")
        return scheduler
    
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Tokyo"))
    
    # Schedule daily report at 9:00 AM JST
    scheduler.add_job(
        send_daily_report,
        CronTrigger(hour=9, minute=0, timezone=pytz.timezone("Asia/Tokyo")),
        id="daily_report",
        name="Daily Analytics Report",
        replace_existing=True
    )
    
    print("[SCHEDULER] Initialized - Daily report scheduled for 9:00 AM JST")
    return scheduler


def start_scheduler():
    """Start the scheduler."""
    global scheduler
    
    if scheduler is None:
        scheduler = init_scheduler()
    
    if not scheduler.running:
        scheduler.start()
        print("[SCHEDULER] Started")


def stop_scheduler():
    """Stop the scheduler."""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
        print("[SCHEDULER] Stopped")


async def trigger_report_now():
    """Manually trigger the daily report (for testing)."""
    print("[SCHEDULER] Manually triggering daily report...")
    await send_daily_report()
