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

from app.prompt_context import get_context

# ── Gemini REST config ─────────────────────────────────────────────────────────────
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_GEMINI_BASE    = "https://generativelanguage.googleapis.com/v1beta/models"
# Model fallback list — tries each in order until one succeeds
_MODEL_FALLBACKS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash-001",
]


# ── Curated TCG Source Intelligence ───────────────────────────────────────────
# These are the authoritative community sources to use when writing articles.
# Reference their content, community narrative, and framing when relevant.
_POKEMON_SOURCES = """
Pokémon TCG Authoritative Sources:
- PTCGRadio (Wossy): Daily meta news, competitive deck breakdowns, Japanese set leaks. Use for competitive hype and set reveal angles.
- LittleDarkFury: Pack-opening and casual collector community. Use for chase card hype and pull-rate discussions.
- Tricky Gym: High-energy deck building and competitive gameplay. Use for emerging rogue deck strategies.
- DeepPocketMonster: Storytelling and high-value collecting. Use for narrative angles on vintage or high-rarity modern cards.
- PokeBeach (pokebeach.com): Fastest source for Japanese card leaks, translations, and set lists before English markets.
- PokeGuardian (pokeguardian.com): Daily updates on promos, merchandise, and tournament results.
- JustinBasil (justinbasil.com): Ultimate deck-building resource. Use to verify meta relevance of newly revealed cards.
"""

_ONEPIECE_SOURCES = """
One Piece TCG Authoritative Sources:
- Joy Boys (YouTube): One Piece TCG news, card info, and match breakdowns. Use for community sentiment on new Leader cards.
- VVTheory (YouTube): High-level deck breakdowns and meta analysis from former MTG players. Use for gameplay strategies and card synergies.
- One Piece Top Decks (X/Web): Central hub for winning tournament lists from Eastern (Asia) and Western metas. Use for shifting tournament trends.
- Official ONE PIECE Card Game Website (en.onepiece-cardgame.com): Announcements, ban lists, and set release dates.
- Spellmana (spellmana.com): Guides and resources. Use for beginner-friendly explanations of complex mechanics.
- TCGplayer Infinite One Piece section: Market watch, price spikes, and set reviews. Use for "Most Expensive Cards" lists and treasure/hype narrative.
"""


async def _call_gemini(user_prompt: str, system_prompt: str) -> str:
    """Call Gemini REST API, trying model fallbacks until one works."""
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 8192},
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
            "Primary keyword: 'Pokémon TCG Japan'. Include card names naturally. "
            "Ground your article in insights from PTCGRadio (Wossy) for competitive meta angles, "
            "PokeBeach for Japanese set leaks and translations, and "
            "PokeGuardian for recent promo and tournament news. "
            "Reference LittleDarkFury's community perspective for chase card hype angles. "
            "Use JustinBasil for verifying meta relevance of newly revealed cards."
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
            "Primary keyword: 'Pokémon anime 2025'. Mention related Pokémon TCG cards naturally. "
            "Draw on DeepPocketMonster's storytelling style for narrative and emotional angles "
            "that connect anime moments to collectible card value."
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
            "Primary keyword: 'One Piece TCG Japan'. Include card names naturally. "
            "Ground your article in tournament data from One Piece Top Decks for meta trends, "
            "VVTheory's high-level deck analysis for strategy angles, and "
            "TCGplayer Infinite's One Piece section for price spike and value narrative. "
            "Reference Joy Boys for community sentiment on new Leader cards. "
            "Use official en.onepiece-cardgame.com for ban list and release date accuracy."
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
            "Primary keyword: 'One Piece anime 2025'. Mention related One Piece TCG cards naturally. "
            "Use Spellmana's approachable writing style for mechanics explanations. "
            "Draw on Joy Boys for community hype framing around key story moments and card tie-ins."
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
            "Draw on knowledge from these authoritative sources to frame the most relevant story: "
            "PokeBeach and PokeGuardian for Pokémon TCG leaks/promos/tournament results; "
            "PTCGRadio (Wossy) and Tricky Gym for competitive meta shifts; "
            "One Piece Top Decks and TCGplayer Infinite for One Piece TCG tournament and price trends; "
            "the official One Piece Card Game site for ban list or set announcements. "
            "Summarise what's happening and why it matters to collectors and players. "
            "Structure the article around 2-3 distinct news items, not just one. "
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

TODAY'S DATE: {today}. Always write about events, releases, and news from {month_year} or the
very near future. Never reference past years as 'current'. If you mention a year, it must be
{year} or later.

You have deep knowledge of the following authoritative TCG community sources. When writing
about Pokémon TCG, draw on the framing, narratives, and topics covered by:
{pokemon_sources}
When writing about One Piece TCG, draw on the framing, narratives, and topics covered by:
{onepiece_sources}
Cite or reference these creators/sites naturally where relevant (e.g. "as PTCGRadio reported",
"according to PokeBeach", "tournament data from One Piece Top Decks shows...").

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

    # Build a date-aware system prompt
    now_dt = datetime.now(timezone.utc)
    today_str = now_dt.strftime("%B %d, %Y")        # e.g. "March 05, 2026"
    month_year_str = now_dt.strftime("%B %Y")       # e.g. "March 2026"
    year_str = str(now_dt.year)                     # e.g. "2026"
    system_prompt = _SYSTEM_PROMPT.format(
        today=today_str,
        month_year=month_year_str,
        year=year_str,
        pokemon_sources=_POKEMON_SOURCES,
        onepiece_sources=_ONEPIECE_SOURCES,
    ) + "\n\n" + get_context("blog")

    topic = _pick_topic()
    logger.info(f"[BLOG] Generating article — category: {topic['category']}")

    # Replace any static year in topic prompt with current year
    topic_prompt = topic['prompt_focus'].replace("2025", year_str)

    user_prompt = (
        f"{topic_prompt}\n\n"
        f"Today's date is {today_str}. Write about topics relevant to {month_year_str}. "
        "Remember: output ONLY Markdown. First line = # Title. "
        "Second line = > meta: [description]. Then article body with ## subheadings."
    )

    try:
        raw = await _call_gemini(user_prompt, system_prompt)
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
    except Exception as e:
        db_session.rollback()
        logger.error(f"[BLOG] DB save failed: {e}")
        return None

    # ── Fire Zapier webhook (non-blocking) ────────────────────────────────────────
    zapier_url = os.getenv("ZAPIER_WEBHOOK_URL", "")
    if zapier_url:
        try:
            base_url = os.getenv("SITE_URL", "https://tcgnakama.com")
            # Build a plain-text excerpt from the markdown body
            excerpt = re.sub(r"[#*\[\]()>\-_`]", "", body_markdown)[:300].strip()
            payload = {
                "blog_url": f"{base_url}/blog/{post.slug}",
                "title": post.title,
                "category": post.category,
                "tags": post.tags,
                "excerpt": excerpt,
                "published_at": post.published_at.isoformat() if post.published_at else "",
                "slug": post.slug,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(zapier_url, json=payload)
            logger.info(f"[BLOG] Zapier webhook fired for '{post.slug}'")
        except Exception as e:
            logger.warning(f"[BLOG] Zapier webhook failed (non-critical): {e}")

    return post
