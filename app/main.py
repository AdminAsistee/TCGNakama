from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.routers import store
from app.routers import blog as blog_router
import os
import asyncio
from dotenv import load_dotenv
from app.dependencies import get_shopify_client
from app.background_tasks import start_background_tasks, stop_background_tasks, get_sync_status

load_dotenv(override=True)

app = FastAPI(title="TCG Nakama")

@app.on_event("startup")
async def startup_event():
    # Initialize database
    from app.database import init_db, SessionLocal
    from app.models import Banner, SystemSetting
    
    init_db()
    print("[STARTUP] Database tables initialized")
    
    # Seed default banners if none exist
    db = SessionLocal()
    try:
        banner_count = db.query(Banner).count()
        # Migrate any banner paths from .jpg/.png to .webp
        banners_to_fix = db.query(Banner).filter(
            Banner.image_path.isnot(None)
        ).all()
        fixed = 0
        for b in banners_to_fix:
            if b.image_path and (b.image_path.endswith('.jpg') or b.image_path.endswith('.png') or b.image_path.endswith('.jpeg')):
                import re
                b.image_path = re.sub(r'\.(jpg|jpeg|png)$', '.webp', b.image_path)
                fixed += 1
        if fixed:
            db.commit()
            print(f"[STARTUP] Migrated {fixed} banner image_path(s) to .webp")

        # Migrate banner cta_link values to #collection: handles
        cta_link_map = {
            'Shop One Piece':   '#collection:one-piece',
            'Shop Now':         '#collection:one-piece',
            'Shop Romance Dawn':'#collection:one-piece',
            'Shop Pokémon':     '#collection:pokemon',
            'Shop Pokemon':     '#collection:pokemon',
            'Shop MTG':         '#collection:magic-tg',
            'Shop MG':          '#collection:magic-tg',
            'Shop Magic':       '#collection:magic-tg',
        }
        cta_fixed = 0
        for b in db.query(Banner).all():
            if b.cta_link == '/' and b.cta_label in cta_link_map:
                b.cta_link = cta_link_map[b.cta_label]
                cta_fixed += 1
        if cta_fixed:
            db.commit()
            print(f"[STARTUP] Migrated {cta_fixed} banner cta_link(s) to #collection: handles")

        if banner_count == 0:
            print("[STARTUP] Seeding default banners...")
            default_banners = [
                Banner(
                    title="One Piece: Four Emperors",
                    subtitle="The ultimate pirate cards have arrived",
                    cta_label="Shop One Piece",
                    cta_link="/",
                    gradient="from-red-900 via-orange-900 to-amber-900",
                    image_path=None,
                    display_order=1,
                    is_active=True
                ),
                Banner(
                    title="Pokémon Scarlet & Violet",
                    subtitle="Explore the latest expansion — chase the illustrators",
                    cta_label="Shop Pokémon",
                    cta_link="/",
                    gradient="from-violet-900 via-purple-900 to-indigo-900",
                    image_path=None,
                    display_order=2,
                    is_active=True
                ),
                Banner(
                    title="One Piece: Romance Dawn",
                    subtitle="Where the legend began — Romance Dawn collection",
                    cta_label="Shop Romance Dawn",
                    cta_link="/",
                    gradient="from-sky-900 via-cyan-900 to-teal-900",
                    image_path=None,
                    display_order=3,
                    is_active=True
                ),
            ]
            db.add_all(default_banners)
            db.commit()
            print(f"[STARTUP] Seeded {len(default_banners)} default banners")
    finally:
        db.close()
    
    # Start background Shopify sync (30-minute polling)
    start_background_tasks()
    
    # Start price tracker scheduler (PriceCharting batch updates)
    from app.scheduler import start_scheduler as start_price_scheduler
    start_price_scheduler()
    print("[STARTUP] Price tracker scheduler initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of background tasks."""
    await stop_background_tasks()
    from app.scheduler import stop_scheduler as stop_price_scheduler
    stop_price_scheduler()
    print("[SHUTDOWN] Application shutdown complete")

# Mount static files with absolute path
from pathlib import Path
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
# Include routers
app.include_router(store.router)

from app.routers import admin
app.include_router(admin.router, prefix="/admin", tags=["admin"])

from app.routers import oauth
app.include_router(oauth.router, tags=["oauth"])

# Blog routes (/blog, /blog/{slug}, /admin/blog)
app.include_router(blog_router.router, tags=["blog"])

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
    # Legacy: email report trigger (disabled)
    return {"success": False, "message": "Report trigger disabled"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)


# ─────────────────────────────────────────────
# About Page
# ─────────────────────────────────────────────
from fastapi.templating import Jinja2Templates as _Jinja2Templates
_templates = _Jinja2Templates(directory="app/templates")

@app.get("/about", response_class=HTMLResponse, include_in_schema=False)
async def about_page(request: Request):
    """Static About page — company info, catalogue, condition guide."""
    from app.dependencies import get_shopify_client
    from urllib.parse import unquote
    shopify = get_shopify_client()
    cart_count = 0
    try:
        cart_id_raw = request.cookies.get("cart_id")
        cart_id = unquote(cart_id_raw) if cart_id_raw else None
        if cart_id:
            cart = await shopify.get_cart(cart_id)
            if cart:
                cart_count = sum(edge["node"].get("quantity", 0) for edge in cart.get("lines", {}).get("edges", []))
    except Exception:
        pass
    return _templates.TemplateResponse("about.html", {"request": request, "cart_count": cart_count})


# ─────────────────────────────────────────────
# SEO: robots.txt
# ─────────────────────────────────────────────
from fastapi.responses import PlainTextResponse, Response

@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt():
    content = """\
# TCGNakama — robots.txt

# Standard crawlers
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /cart/
Disallow: /api/
Disallow: /refresh

# Explicitly allow major AI citation & training crawlers
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: GoogleOther
Allow: /

User-agent: anthropic-ai
Allow: /

Sitemap: https://tcgnakama.com/sitemap.xml
LLMs: https://tcgnakama.com/llms.txt
"""
    return PlainTextResponse(content, media_type="text/plain")


# ─────────────────────────────────────────────
# SEO: sitemap.xml — dynamically built from Shopify products
# ─────────────────────────────────────────────
@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    from app.background_tasks import get_cached_products
    from app.database import SessionLocal
    from app.models import BlogPost
    from datetime import date

    today = date.today().isoformat()
    base_url = "https://tcgnakama.com"

    # Static pages
    urls = [
        f"""  <url>
    <loc>{base_url}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
    <lastmod>{today}</lastmod>
  </url>""",
        f"""  <url>
    <loc>{base_url}/blog</loc>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
    <lastmod>{today}</lastmod>
  </url>""",
        f"""  <url>
    <loc>{base_url}/about</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
    <lastmod>{today}</lastmod>
  </url>""",
    ]

    # Blog post URLs from DB
    try:
        db = SessionLocal()
        blog_posts = db.query(BlogPost).filter(BlogPost.is_published == True).all()
        db.close()
        for post in blog_posts:
            lastmod = post.published_at.date().isoformat() if post.published_at else today
            urls.append(f"""  <url>
    <loc>{base_url}/blog/{post.slug}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
    <lastmod>{lastmod}</lastmod>
  </url>""")
    except Exception:
        pass

    # Dynamic card pages from cache
    products = get_cached_products() or []
    for product in products:
        safe_id = product.get("safe_id") or ""
        if not safe_id:
            gid = product.get("id", "")
            safe_id = gid.split("/")[-1] if "/" in gid else gid
        if safe_id:
            urls.append(f"""  <url>
    <loc>{base_url}/card/{safe_id}</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
    <lastmod>{today}</lastmod>
  </url>""")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>"

    return Response(content=xml, media_type="application/xml")


# ─────────────────────────────────────────────
# AI Discoverability: llms.txt
# ─────────────────────────────────────────────
@app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
async def llms_txt():
    content = """\
# TCGNakama

> Japan's premier marketplace for Pokémon, One Piece, and Magic: The Gathering single cards.

## What We Sell
- **Pokémon TCG** — Japanese and international singles, Scarlet & Violet series, all SV sets
- **One Piece TCG** — All OP sets (OP01 through latest), singles in all rarities
- **Magic: The Gathering** — Japanese market singles, all formats

## How It Works
- Browse the full marketplace at https://tcgnakama.com/
- All prices are listed in **Japanese Yen (JPY)**
- Cards are graded by condition: NM (Near Mint), LP (Lightly Played), MP (Moderately Played), HP (Heavily Played), Raw
- Package types available: Raw · Toploader · Booster Pack · Slab (PSA / BGS / CGC graded)
- Live market value comparison powered by PriceCharting data
- Secure checkout via Shopify — ships next day from Japan

## Fresh Pulls
- Newly listed cards appear in the "Fresh Pulls" section on the homepage
- "What's Hot" section shows cards with the biggest recent price gains

## Key Pages
- Marketplace homepage: https://tcgnakama.com/
- Individual card pages: https://tcgnakama.com/card/{id}
- Sitemap: https://tcgnakama.com/sitemap.xml

## Trust & Authenticity
- Authenticity guaranteed on all cards
- Secure, tracked shipping from Japan
- Market-priced using real-time PriceCharting data
- Inventory synced live with Shopify

## About
TCGNakama is a Japan-based TCG card marketplace specialising in Pokémon, One Piece, and Magic: The Gathering singles.
Cards are sourced, authenticated, and shipped directly from Japan.
"""
    return PlainTextResponse(content, media_type="text/plain")
