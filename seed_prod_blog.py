"""
Trigger blog generation directly against production PostgreSQL.
"""
import asyncio, os
os.environ["DATABASE_URL"] = (
    "postgresql://doadmin:AVNS_WJtLYtseYwMSXA15Q5w@"
    "app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com"
    ":25060/defaultdb?sslmode=require"
)
from dotenv import load_dotenv
load_dotenv()

async def main():
    from app.database import SessionLocal
    from app.services.blog_generator import generate_article
    db = SessionLocal()
    try:
        print("Generating article...")
        post = await generate_article(db)
        if post:
            print(f"SUCCESS: '{post.title}'")
            print(f"  slug: {post.slug}")
            print(f"  category: {post.category}")
            print(f"  published: {post.is_published}")
        else:
            print("generate_article returned None (duplicate topic or error)")
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

asyncio.run(main())
