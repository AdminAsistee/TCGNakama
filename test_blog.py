"""
Test script: generates one blog article and posts it to Facebook Page.
Run from the project root:
    python test_blog.py

Requires these env vars in .env:
    GEMINI_API_KEY
    DATABASE_URL
    FACEBOOK_PAGE_ID
    FACEBOOK_PAGE_ACCESS_TOKEN
"""
import asyncio
import sys
import os

# Always run from project root so relative DB paths work
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

# Fix Windows terminal encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() in ('cp932', 'cp1252', 'ascii'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(override=True)

from app.database import init_db, SessionLocal
from app.services.blog_generator import generate_article
from app.services.facebook_poster import post_to_facebook_group


async def main():
    print("\n=== TCGNakama Blog Test ===\n")

    # 1. Init DB (creates blog_posts table if missing)
    print("[1] Initialising database...")
    init_db()
    print("    OK - Database ready\n")

    # 2. Generate article
    print("[2] Generating article via Gemini AI (may take 10-30s)...")
    db = SessionLocal()
    try:
        post = await generate_article(db)
    finally:
        db.close()

    if not post:
        print("    FAIL - Article generation failed -- check GEMINI_API_KEY and logs above")
        return

    print(f"    OK - Article generated!")
    print(f"       Title    : {post.title}")
    print(f"       Slug     : /blog/{post.slug}")
    print(f"       Category : {post.category}")
    print(f"       Tags     : {post.tags}")
    print(f"       Meta     : {post.meta_description}\n")

    # 3. Post to Facebook
    print("[3] Posting to Facebook Page...")
    fb_id = await post_to_facebook_group(post)

    if fb_id:
        print(f"    OK - Facebook post created! Post ID: {fb_id}")
        print(f"       Check: https://www.facebook.com/{fb_id}\n")
        # Save facebook_post_id back to DB
        db2 = SessionLocal()
        try:
            from app.models import BlogPost
            saved = db2.query(BlogPost).filter_by(id=post.id).first()
            if saved:
                saved.facebook_post_id = fb_id
                db2.commit()
                print("    OK - Facebook post ID saved to DB")
        finally:
            db2.close()
    elif not os.getenv("FACEBOOK_PAGE_ID"):
        print("    SKIP - FACEBOOK_PAGE_ID not set (add to .env to enable)")
    else:
        print("    FAIL - Facebook post failed -- check FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN")

    print(f"\n=== Done! Blog post live at: http://localhost:8001/blog/{post.slug} ===\n")


if __name__ == "__main__":
    asyncio.run(main())
