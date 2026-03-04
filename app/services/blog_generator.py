"""
Blog Generator Service — TCGNakama
Uses Google Gemini AI with Google Search grounding to generate SEO-optimised
TCG/anime blog articles. Rotates across 6 topic categories.
"""
import os
import re
import random
import logging
from datetime import datetime, timezone
from typing import Optional

import markdown as md_lib

import httpx

logger = logging.getLogger(__name__)

# ── Gemini REST config ─────────────────────────────────────────────────────────────
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_GEMINI_BASE    = "https://generativelanguage.googleapis.com/v1beta/models"
# Model fallback list — tries each in order until one succeeds
_MODEL_FALLBACKS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
]


async def _call_gemini(user_prompt: str, system_prompt: str) -> str:
    """Call Gemini REST API, trying model fallbacks until one works."""
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 2048},
    }
    last_error = "unknown error"
    async with httpx.AsyncClient(timeout=60.0) as client:
        for model in _MODEL_FALLBACKS:
            url = f"{_GEMINI_BASE}/{model}:generateContent?key={_GEMINI_API_KEY}"
            try:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if resp.status_code == 200 and "candidates" in data:
                    parts = data["candidates"][0]["content"]["parts"]
                    return "".join(p.get("text", "") for p in parts)
                last_error = data.get("error", {}).get("message", str(data))
                logger.warning(f"[BLOG] Model {model} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[BLOG] Model {model} exception: {e}")
    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


# ── Topic Rotation ─────────────────────────────────────────────────────────────
TOPIC_POOL = [
    {
        "category": "pokemon",
        "weight": 3,
        "prompt_focus": (
            "Write a 700-900 word blog article about the latest Pokémon TCG news. "
            "Topics may include: new set reveals (Scarlet & Violet era), special Illustration Rare cards, "
            "Pikachu ex cards, Charizard prices, upcoming Japanese set releases, or tournament meta. "
            "Primary keyword: 'Pokémon TCG Japan'. Include card names naturally."
        ),
        "tags": "pokemon, pokemon tcg, scarlet violet, japanese cards, tcg japan",
    },
    {
        "category": "pokemon",
        "weight": 2,
        "prompt_focus": (
            "Write a 700-900 word blog article about the Pokémon anime or movies. "
            "Topics may include: recent Pokémon anime episodes, Pokémon movie releases, "
            "character lore (Pikachu, Ash, Liko, Roy), or the new anime series. "
            "Primary keyword: 'Pokémon anime 2025'. Mention related Pokémon TCG cards naturally."
        ),
        "tags": "pokemon, pokemon anime, pikachu, pokemon movie, tcg",
    },
    {
        "category": "onepiece",
        "weight": 2,
        "prompt_focus": (
            "Write a 700-900 word blog article about One Piece TCG. "
            "Topics may include: new One Piece card set reveals, Luffy Leader cards, "
            "One Piece TCG price spikes, tournament results, or tips for building One Piece decks. "
            "Primary keyword: 'One Piece TCG Japan'. Include card names naturally."
        ),
        "tags": "one piece, one piece tcg, luffy, op cards, tcg japan",
    },
    {
        "category": "anime",
        "weight": 2,
        "prompt_focus": (
            "Write a 700-900 word blog article about One Piece anime or movies. "
            "Topics may include: latest One Piece episodes, One Piece Film Red or similar movies, "
            "character lore (Monkey D. Luffy, Zoro, Nami, Shanks), arc summaries, or upcoming sagas. "
            "Primary keyword: 'One Piece anime 2025'. Mention related One Piece TCG cards naturally."
        ),
        "tags": "one piece, one piece anime, luffy, one piece film, tcg",
    },
    {
        "category": "mtg",
        "weight": 1,
        "prompt_focus": (
            "Write a 700-900 word blog article about Magic: The Gathering in Japan. "
            "Topics may include: new MTG set releases (Japanese editions), commander staples, "
            "MTG price movements in JPY, Japanese art variants, or MTG tournament news in Japan. "
            "Primary keyword: 'Magic The Gathering Japan'. Include card names naturally."
        ),
        "tags": "magic the gathering, mtg, mtg japan, commander, japanese mtg",
    },
    {
        "category": "tips",
        "weight": 1,
        "prompt_focus": (
            "Write a 700-900 word blog article with tips for TCG collectors and investors. "
            "Topics may include: how to grade Pokémon cards for PSA/BGS/CGC, "
            "how to identify near-mint vs lightly played condition, "
            "tips for buying authentic Japanese TCG cards online, "
            "or how card condition affects resale value. "
            "Primary keyword: 'TCG card collecting Japan'."
        ),
        "tags": "tcg collecting, card grading, psa, near mint, japanese cards",
    },
    {
        "category": "news",
        "weight": 2,
        "prompt_focus": (
            "Write a 700-900 word blog article about the latest TCG market news. "
            "Use Google Search to find the most recent actual news about Pokémon TCG, "
            "One Piece TCG, or Magic: The Gathering from the past week. "
            "Summarise what's happening and why it matters to collectors and players. "
            "Primary keyword: 'TCG news 2025 Japan'."
        ),
        "tags": "tcg news, pokemon news, one piece tcg news, mtg news, trading cards",
    },
]


def _pick_topic() -> dict:
    """Weighted random topic selection."""
    population = []
    for t in TOPIC_POOL:
        population.extend([t] * t["weight"])
    return random.choice(population)


def _slugify(title: str) -> str:
    """Convert title to a URL-safe slug."""
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:120]


# ── Core article generation ────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are an expert TCG content writer for TCGNakama, a Japan-based marketplace
for Pokémon, One Piece, and Magic: The Gathering single cards.

Your articles must:
1. Be written in clear, engaging English for a global TCG audience.
2. Include the primary keyword naturally in the FIRST paragraph and 2-3 more times throughout.
3. Have a logical structure with H2/H3 subheadings (use Markdown ##/###).
4. Include 2-3 internal links to TCGNakama using this exact format:
   [shop Pokémon cards at TCGNakama](https://tcgnakama.com/#all-cards-section)
   [TCGNakama marketplace](https://tcgnakama.com/)
   [buy One Piece TCG cards](https://tcgnakama.com/#all-cards-section)
   Vary the anchor text naturally — DO NOT use the same anchor twice.
5. End with a short CTA paragraph encouraging readers to browse TCGNakama.com.
6. Output ONLY the article in Markdown format. No meta description, no extra JSON.
   The very FIRST line must be the article title as: # Title Here
   The SECOND line must be the meta description as: > meta: [155 char max description here]
   Then the article body follows."""


async def generate_article(db_session) -> Optional[object]:
    """
    Generate a blog post using Gemini and save it to the database.
    Returns the saved BlogPost object, or None on failure.
    """
    from app.models import BlogPost

    if not _GEMINI_API_KEY:
        logger.error("[BLOG] GEMINI_API_KEY not set — skipping blog generation.")
        return None

    topic = _pick_topic()
    logger.info(f"[BLOG] Generating article — category: {topic['category']}")

    user_prompt = (
        f"{topic['prompt_focus']}\n\n"
        "Remember: output ONLY Markdown. First line = # Title. "
        "Second line = > meta: [description]. Then article body with ## subheadings."
    )

    try:
        raw = await _call_gemini(user_prompt, _SYSTEM_PROMPT)
        raw = raw.strip()
    except Exception as e:
        logger.error(f"[BLOG] Gemini generation failed: {e}")
        return None


    # ── Parse the output ────────────────────────────────────────────────────
    lines = raw.split("\n")
    title = "TCGNakama Blog"
    meta_description = ""
    body_start = 0

    # Extract title from first # heading
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body_start = i + 1
            break

    # Extract meta description from > meta: line
    for i, line in enumerate(lines[body_start:], start=body_start):
        if line.startswith("> meta:"):
            meta_description = line.replace("> meta:", "").strip()[:155]
            body_start = i + 1
            break

    # Remaining lines = article body
    body_markdown = "\n".join(lines[body_start:]).strip()

    # Convert Markdown → HTML
    content_html = md_lib.markdown(
        body_markdown,
        extensions=["extra", "nl2br", "sane_lists", "toc"],
    )

    # Generate unique slug
    base_slug = _slugify(title)
    slug = base_slug
    suffix = 1
    while db_session.query(BlogPost).filter_by(slug=slug).first():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    now = datetime.now(timezone.utc)

    post = BlogPost(
        slug=slug,
        title=title,
        meta_description=meta_description or title[:155],
        content_markdown=body_markdown,
        content_html=content_html,
        category=topic["category"],
        tags=topic["tags"],
        is_published=True,
        published_at=now,
    )

    try:
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        logger.info(f"[BLOG] ✅ Published: '{post.title}' → /blog/{post.slug}")
        return post
    except Exception as e:
        db_session.rollback()
        logger.error(f"[BLOG] DB save failed: {e}")
        return None
