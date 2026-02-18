"""
Batch Price Tracker Service for TCG Nakama.
Fetches market prices from PriceCharting API for all products,
stores snapshots in the database for trending/gainers calculations.

Designed for scale: 5,000+ cards at 1 req/sec with smart Gemini ambiguity mode.
"""
import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import httpx

from app.database import SessionLocal
from app.models import PriceSnapshot, SystemSetting

logger = logging.getLogger("price_tracker")

# ---------------------------------------------------------------------------
# Reuse Gemini filter from appraisal.py (only called when >3 ambiguous results)
# ---------------------------------------------------------------------------
_gemini_lock = asyncio.Lock()


async def _gemini_disambiguate(search_query: str, results: list[dict]) -> list[dict]:
    """Call Gemini ONLY when PriceCharting returns >3 ambiguous results (Option 3)."""
    if len(results) <= 3:
        return results  # Clear enough match — skip Gemini

    try:
        import google.generativeai as genai
        import json

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            return results

        async with _gemini_lock:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            results_text = "\n".join([
                f'{i+1}. "{r["name"]}" - ${r["price"]}'
                for i, r in enumerate(results[:20])  # Cap at 20 to save tokens
            ])

            prompt = f"""You are a TCG card pricing expert. I need the market value for: "{search_query}"

PriceCharting returned these results:
{results_text}

Select the BEST match following these priorities:
1. Card number match (highest priority)
2. REGULAR version preferred over [Alt Art], [Promo], [Parallel], [Serial], [Ichiban Kuji]
3. ENGLISH version preferred over Japanese
4. Base card name must match

Return ONLY the indices as a JSON array, e.g. [1] or [2, 5]. If no match: []"""

            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # Parse JSON
            if "```" in response_text:
                json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            indices = json.loads(response_text)
            if indices:
                filtered = [results[i - 1] for i in indices if 0 < i <= len(results)]
                if filtered:
                    logger.info(f"  Gemini: {len(results)} → {len(filtered)} matches")
                    return filtered

    except Exception as e:
        logger.warning(f"  Gemini error: {e}, using direct match")

    return results


# ---------------------------------------------------------------------------
# PriceCharting API call (single card)
# ---------------------------------------------------------------------------

def _extract_search_name(card_name: str) -> str:
    """Extract English name from card title (handles Japanese+English format)."""
    paren_match = re.search(r'\(([^)]+)\)', card_name)
    if paren_match:
        return paren_match.group(1).strip()
    return card_name.split('(')[0].strip()


def _extract_price_from_product(product: dict) -> Optional[float]:
    """Extract best price from a PriceCharting product (loose > cib > new)."""
    for key in ('loose-price', 'cib-price', 'new-price'):
        raw = product.get(key)
        if raw:
            try:
                price = float(raw) / 100  # API returns cents
                if price > 0:
                    return price
            except (ValueError, TypeError):
                continue
    return None


async def _fetch_single_price(
    client: httpx.AsyncClient,
    api_key: str,
    card_name: str,
    set_name: str,
    card_number: str,
) -> Optional[float]:
    """
    Fetch market price for a single card from PriceCharting API.
    Applies smart ambiguity mode: Gemini only when >3 results.
    """
    search_name = _extract_search_name(card_name)

    query_parts = [search_name]
    if set_name and set_name not in ("Unknown", "Unknown Set", ""):
        query_parts.append(set_name)
    if card_number:
        query_parts.append(card_number.replace('#', ''))

    search_query = " ".join(query_parts)
    url = f"https://www.pricecharting.com/api/products?t={api_key}&q={quote_plus(search_query)}"

    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return None

        data = resp.json()
        products = data.get("products", [])
        if not products:
            return None

        # Collect valid prices
        valid = []
        for p in products:
            price = _extract_price_from_product(p)
            if price:
                valid.append({"name": p.get("product-name", "?"), "price": price})

        if not valid:
            return None

        # Filter by card number if available
        if card_number:
            clean_num = card_number.replace('#', '').upper()
            num_variations = {clean_num, re.sub(r'[-/\s]', '', clean_num)}
            first = re.split(r'[/-]', clean_num)[0].strip()
            num_variations.add(first)
            num_variations.add(first.lstrip('0') or '0')

            number_matches = [
                v for v in valid
                if any(var in v["name"].upper() for var in num_variations)
            ]
            if number_matches:
                valid = number_matches

        # Smart Ambiguity Mode (Option 3): Gemini only when >3 results
        valid = await _gemini_disambiguate(search_query, valid)

        # Pick cheapest from remaining (regular version is typically cheapest)
        best = min(valid, key=lambda x: x["price"])
        return best["price"]

    except Exception as e:
        logger.warning(f"  API error for '{search_name}': {e}")
        return None


# ---------------------------------------------------------------------------
# Exchange rate
# ---------------------------------------------------------------------------

async def _get_usd_to_jpy() -> float:
    """Fetch current USD→JPY rate from Frankfurter. Returns fallback 150.0 on failure."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://api.frankfurter.dev/v1/latest?base=USD&symbols=JPY")
            if resp.status_code == 200:
                rate = resp.json()["rates"]["JPY"]
                logger.info(f"Exchange rate: 1 USD = {rate} JPY")
                return float(rate)
    except Exception as e:
        logger.warning(f"Frankfurter API error: {e}, using fallback rate")
    return 150.0


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

CHUNK_SIZE = 500  # Process products in chunks for progress logging


async def run_batch_update(products: list[dict]) -> dict:
    """
    Main batch entry point: fetches market prices for ALL products,
    stores PriceSnapshot rows.

    Args:
        products: List of product dicts from ShopifyClient.get_products()

    Returns:
        dict with stats: {updated, failed, skipped, total, duration_sec}
    """
    start = datetime.utcnow()
    api_key = os.getenv("PRICECHARTING_API_KEY")
    if not api_key:
        logger.error("PRICECHARTING_API_KEY not set — aborting batch")
        return {"updated": 0, "failed": 0, "skipped": 0, "total": len(products),
                "duration_sec": 0, "error": "No API key"}

    # 1. Get exchange rate ONCE
    usd_to_jpy = await _get_usd_to_jpy()

    # 2. Process all products
    updated = 0
    failed = 0
    skipped = 0
    total = len(products)

    logger.info(f"=== BATCH PRICE UPDATE: {total} products ===")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, product in enumerate(products):
            card_name = product.get("title", "")
            set_name = product.get("set", "")
            card_number = product.get("card_number", "")
            product_id = product.get("id", "")

            # Skip cards without proper identification
            if not card_name or card_name == "Draft":
                skipped += 1
                continue

            # Chunk progress logging
            if i > 0 and i % CHUNK_SIZE == 0:
                logger.info(f"  Progress: {i}/{total} "
                            f"(updated={updated}, failed={failed}, skipped={skipped})")

            # Throttle: 1 request per 1.1 seconds (PriceCharting limit is 1/sec)
            if i > 0:
                await asyncio.sleep(1.1)

            try:
                price_usd = await _fetch_single_price(
                    client, api_key, card_name, set_name, card_number
                )

                if price_usd is None:
                    failed += 1
                    continue

                price_jpy = int(price_usd * usd_to_jpy)

                # Store snapshot in DB
                db = SessionLocal()
                try:
                    snapshot = PriceSnapshot(
                        product_id=product_id,
                        product_title=card_name,
                        market_usd=price_usd,
                        market_jpy=price_jpy,
                        exchange_rate=usd_to_jpy,
                        recorded_at=datetime.utcnow(),
                    )
                    db.add(snapshot)
                    db.commit()
                    updated += 1
                except Exception as db_err:
                    db.rollback()
                    logger.error(f"  DB error for '{card_name}': {db_err}")
                    failed += 1
                finally:
                    db.close()

            except Exception as e:
                logger.error(f"  Unexpected error for '{card_name}': {e}")
                failed += 1

    duration = (datetime.utcnow() - start).total_seconds()
    logger.info(f"=== BATCH COMPLETE: {updated}/{total} updated, "
                f"{failed} failed, {skipped} skipped in {duration:.0f}s ===")

    # Save last-run metadata
    _save_run_metadata(updated, failed, skipped, total, duration)

    return {
        "updated": updated, "failed": failed, "skipped": skipped,
        "total": total, "duration_sec": round(duration, 1),
    }


def _save_run_metadata(updated: int, failed: int, skipped: int,
                       total: int, duration: float):
    """Persist last batch run stats in SystemSetting table."""
    db = SessionLocal()
    try:
        metadata = {
            "price_tracker_last_run": datetime.utcnow().isoformat(),
            "price_tracker_last_updated": str(updated),
            "price_tracker_last_failed": str(failed),
            "price_tracker_last_skipped": str(skipped),
            "price_tracker_last_total": str(total),
            "price_tracker_last_duration": f"{duration:.0f}",
        }
        for key, value in metadata.items():
            existing = db.query(SystemSetting).filter_by(key=key).first()
            if existing:
                existing.value = value
            else:
                db.add(SystemSetting(key=key, value=value))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save run metadata: {e}")
    finally:
        db.close()
