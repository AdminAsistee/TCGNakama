"""
Blog router — TCGNakama
Public routes: /blog (list) and /blog/{slug} (individual post)
Admin routes: /admin/blog (management)
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import BlogPost
from app.dependencies import get_shopify_client, ShopifyClient
from datetime import datetime, timezone
from urllib.parse import unquote

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

POSTS_PER_PAGE = 9


# ── Public: Blog list ──────────────────────────────────────────────────────────
@router.get("/blog", response_class=HTMLResponse)
async def blog_list(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    client: ShopifyClient = Depends(get_shopify_client),
):
    offset = (page - 1) * POSTS_PER_PAGE
    total = db.query(BlogPost).filter(BlogPost.is_published == True).count()
    posts = (
        db.query(BlogPost)
        .filter(BlogPost.is_published == True)
        .order_by(BlogPost.published_at.desc())
        .offset(offset)
        .limit(POSTS_PER_PAGE)
        .all()
    )
    total_pages = (total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE

    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    cart_count = 0
    if cart_id:
        cart_data = await client.get_cart(cart_id)
        if cart_data:
            cart_count = cart_data.get("totalQuantity", 0)

    return templates.TemplateResponse("blog_list.html", {
        "request": request,
        "posts": posts,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "cart_count": cart_count,
    })


# ── Public: Individual post ────────────────────────────────────────────────────
@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    client: ShopifyClient = Depends(get_shopify_client),
):
    post = db.query(BlogPost).filter(
        BlogPost.slug == slug,
        BlogPost.is_published == True,
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Article not found")

    related = (
        db.query(BlogPost)
        .filter(BlogPost.is_published == True, BlogPost.id != post.id)
        .order_by(BlogPost.published_at.desc())
        .limit(3)
        .all()
    )

    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    cart_count = 0
    if cart_id:
        cart_data = await client.get_cart(cart_id)
        if cart_data:
            cart_count = cart_data.get("totalQuantity", 0)

    return templates.TemplateResponse("blog_post.html", {
        "request": request,
        "post": post,
        "related": related,
        "cart_count": cart_count,
    })


# ── Admin: Blog management ─────────────────────────────────────────────────────
@router.get("/admin/blog", response_class=HTMLResponse)
async def admin_blog_list(request: Request, db: Session = Depends(get_db)):
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
    return templates.TemplateResponse("admin_blog.html", {
        "request": request,
        "posts": posts,
    })


@router.post("/admin/blog/generate", response_class=HTMLResponse)
async def admin_generate_post(request: Request, db: Session = Depends(get_db)):
    """Manually trigger article generation from admin panel."""
    from app.services.blog_generator import generate_article
    post = await generate_article(db)
    if post:
        return RedirectResponse(f"/admin/blog?generated={post.slug}", status_code=303)
    return RedirectResponse("/admin/blog?error=generation_failed", status_code=303)


@router.post("/admin/blog/{post_id}/toggle", response_class=HTMLResponse)
async def admin_toggle_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    """Toggle published/draft status."""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404)
    post.is_published = not post.is_published
    if post.is_published and not post.published_at:
        post.published_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse("/admin/blog", status_code=303)


@router.post("/admin/blog/{post_id}/delete", response_class=HTMLResponse)
async def admin_delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a blog post."""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if post:
        db.delete(post)
        db.commit()
    return RedirectResponse("/admin/blog", status_code=303)
