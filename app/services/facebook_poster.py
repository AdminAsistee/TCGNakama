"""
Facebook Page Poster — TCGNakama (Plugin Stub)

To enable: set FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN in your environment.
The Page Access Token needs the `pages_manage_posts` + `pages_read_engagement` permissions.
No App Review needed to post to your own page.
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

FACEBOOK_PAGE_ID           = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
GRAPH_API_BASE             = "https://graph.facebook.com/v19.0"


async def post_to_facebook_group(post) -> str | None:
    """
    Post a blog article to the TCGNakama Facebook Page.
    Returns the Facebook post ID on success, None if disabled or failed.

    post: BlogPost ORM object
    """
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.info("[FACEBOOK] Credentials not set — skipping Facebook post.")
        return None

    message = (
        f"📰 New article on TCGNakama Blog!\n\n"
        f"🃏 {post.title}\n\n"
        f"{post.excerpt}\n\n"
        f"👉 Read more: https://tcgnakama.com/blog/{post.slug}"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GRAPH_API_BASE}/{FACEBOOK_PAGE_ID}/feed",
                data={
                    "message": message,
                    "link": f"https://tcgnakama.com/blog/{post.slug}",
                    "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
                },
            )
            data = resp.json()

        if "id" in data:
            logger.info(f"[FACEBOOK] ✅ Posted to page — post id: {data['id']}")
            return data["id"]
        else:
            logger.error(f"[FACEBOOK] Post failed: {data}")
            return None

    except Exception as e:
        logger.error(f"[FACEBOOK] Exception during post: {e}")
        return None
