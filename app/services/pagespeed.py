"""
Agent PageSpeed — Google PageSpeed Insights service.
Runs audits against the PSI API, stores results in DB, and respects rate limits.
"""
import json
import logging
import os
import httpx
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import PageSpeedAudit, SystemSetting

logger = logging.getLogger("pagespeed")

PSI_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
RATE_LIMIT_SECONDS = 60
CACHE_HOURS = 24

# Module-level state
_audit_running = False


def is_audit_running() -> bool:
    """Check if an audit is currently in progress."""
    return _audit_running


def get_latest_audit(strategy: str = "mobile") -> dict | None:
    """Return the most recent audit for the given strategy, or None."""
    db = SessionLocal()
    try:
        audit = (
            db.query(PageSpeedAudit)
            .filter(PageSpeedAudit.strategy == strategy)
            .order_by(PageSpeedAudit.created_at.desc())
            .first()
        )
        if not audit:
            return None
        return _audit_to_dict(audit)
    finally:
        db.close()


def get_audit_history(limit: int = 10, strategy: str = "mobile") -> list[dict]:
    """Return the last N audits for trend tracking."""
    db = SessionLocal()
    try:
        audits = (
            db.query(PageSpeedAudit)
            .filter(PageSpeedAudit.strategy == strategy)
            .order_by(PageSpeedAudit.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_audit_to_dict(a) for a in audits]
    finally:
        db.close()


def is_cache_fresh(strategy: str = "mobile") -> bool:
    """Check if the latest audit is less than CACHE_HOURS old."""
    db = SessionLocal()
    try:
        audit = (
            db.query(PageSpeedAudit)
            .filter(PageSpeedAudit.strategy == strategy)
            .order_by(PageSpeedAudit.created_at.desc())
            .first()
        )
        if not audit:
            return False
        return (datetime.utcnow() - audit.created_at) < timedelta(hours=CACHE_HOURS)
    finally:
        db.close()


def _check_rate_limit() -> bool:
    """Return True if we're within rate limit (should NOT call API)."""
    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter_by(key="psi_last_run").first()
        if not row:
            return False
        try:
            last_run = datetime.fromisoformat(row.value)
            return (datetime.utcnow() - last_run).total_seconds() < RATE_LIMIT_SECONDS
        except (ValueError, TypeError):
            return False
    finally:
        db.close()


def _set_last_run():
    """Update the last run timestamp."""
    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter_by(key="psi_last_run").first()
        now_str = datetime.utcnow().isoformat()
        if row:
            row.value = now_str
        else:
            db.add(SystemSetting(key="psi_last_run", value=now_str))
        db.commit()
    finally:
        db.close()


def _set_last_error(msg: str | None):
    """Update the last error message."""
    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter_by(key="psi_last_error").first()
        if row:
            row.value = msg if msg else ""
        elif msg:
            db.add(SystemSetting(key="psi_last_error", value=msg))
        db.commit()
    finally:
        db.close()


async def run_audit(url: str, strategy: str = "mobile") -> dict:
    """
    Run a PageSpeed Insights audit.
    Calls the PSI API, parses the response, and stores in the database.
    Returns a dict with status and scores.
    """
    global _audit_running

    if _audit_running:
        return {"status": "already_running"}

    if _check_rate_limit():
        return {"status": "rate_limited", "message": f"Please wait {RATE_LIMIT_SECONDS}s between audits"}

    _audit_running = True
    logger.info(f"[PAGESPEED] Starting audit for {url} ({strategy})")

    try:
        _set_last_run()
        _set_last_error(None)

        # Call Google PSI API
        params = {
            "url": url,
            "strategy": strategy,
            "category": ["PERFORMANCE", "ACCESSIBILITY", "BEST_PRACTICES", "SEO"],
        }
        api_key = os.getenv("GOOGLE_PAGESPEED_API_KEY")
        if api_key:
            params["key"] = api_key

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(PSI_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        # Parse scores from lighthouse result
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})

        scores = {
            "performance": _extract_score(categories.get("performance", {})),
            "accessibility": _extract_score(categories.get("accessibility", {})),
            "best_practices": _extract_score(categories.get("best-practices", {})),
            "seo": _extract_score(categories.get("seo", {})),
        }

        # Extract top opportunities (audits with savings)
        audits = lighthouse.get("audits", {})
        opportunities = []
        for audit_id, audit_data in audits.items():
            if audit_data.get("score") is not None and audit_data["score"] < 1:
                details = audit_data.get("details", {})
                savings = details.get("overallSavingsMs", 0)
                if savings > 0:
                    opportunities.append({
                        "id": audit_id,
                        "title": audit_data.get("title", audit_id),
                        "description": audit_data.get("description", ""),
                        "savings_ms": round(savings),
                        "score": round((audit_data.get("score", 0) or 0) * 100),
                        "display_value": audit_data.get("displayValue", ""),
                    })

        # Sort by savings descending
        opportunities.sort(key=lambda x: x["savings_ms"], reverse=True)

        # Store in database
        db = SessionLocal()
        try:
            audit_record = PageSpeedAudit(
                url=url,
                strategy=strategy,
                performance_score=scores["performance"],
                accessibility_score=scores["accessibility"],
                best_practices_score=scores["best_practices"],
                seo_score=scores["seo"],
                opportunities_json=json.dumps(opportunities),
                full_response_json=json.dumps(data),
            )
            db.add(audit_record)
            db.commit()
            logger.info(f"[PAGESPEED] Audit complete — Performance: {scores['performance']}")
        finally:
            db.close()

        return {
            "status": "completed",
            "scores": scores,
            "opportunities_count": len(opportunities),
        }

    except httpx.HTTPStatusError as e:
        error_msg = f"PSI API error: {e.response.status_code}"
        logger.error(f"[PAGESPEED] {error_msg}")
        _set_last_error(error_msg)
        return {"status": "error", "message": error_msg}

    except Exception as e:
        error_msg = str(e)[:500]
        logger.error(f"[PAGESPEED] Audit failed: {e}", exc_info=True)
        _set_last_error(error_msg)
        return {"status": "error", "message": error_msg}

    finally:
        _audit_running = False


def _extract_score(category: dict) -> int:
    """Extract score from a PSI category (0-1 float → 0-100 int)."""
    score = category.get("score")
    if score is None:
        return 0
    return round(score * 100)


def _audit_to_dict(audit: PageSpeedAudit) -> dict:
    """Convert a PageSpeedAudit ORM object to a plain dict."""
    return {
        "id": audit.id,
        "url": audit.url,
        "strategy": audit.strategy,
        "performance_score": audit.performance_score,
        "accessibility_score": audit.accessibility_score,
        "best_practices_score": audit.best_practices_score,
        "seo_score": audit.seo_score,
        "opportunities": json.loads(audit.opportunities_json) if audit.opportunities_json else [],
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
    }
