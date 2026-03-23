"""
Test blog generation against the production database/API.
Run this locally with the production env vars if needed.
"""
import asyncio
import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

async def test():
    print(f"GEMINI_API_KEY set: {'yes' if os.getenv('GEMINI_API_KEY') else 'NO - MISSING!'}")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:40]}...")

    try:
        import markdown
        print(f"markdown package: OK (v{markdown.__version__})")
    except ImportError as e:
        print(f"markdown package: MISSING - {e}")
        return

    try:
        from app.database import SessionLocal, init_db
        from app.models import BlogPost
        init_db()
        db = SessionLocal()
        count = db.query(BlogPost).count()
        print(f"BlogPost table: OK ({count} posts)")
        db.close()
    except Exception as e:
        print(f"DB error: {e}")
        return

    try:
        from app.services.blog_generator import generate_article
        print("blog_generator import: OK")
    except Exception as e:
        print(f"blog_generator import FAILED: {e}")
        return

    print("\nGenerating article...")
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        post = await generate_article(db)
        if post:
            print(f"SUCCESS: '{post.title}'")
        else:
            print("generate_article returned None (duplicate/error)")
        db.close()
    except Exception as e:
        import traceback
        print(f"generate_article FAILED: {e}")
        traceback.print_exc()

asyncio.run(test())
