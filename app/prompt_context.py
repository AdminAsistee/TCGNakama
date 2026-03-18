"""
Prompt Context — Grounding context for all Gemini AI calls.
Loads domain ontology and agent-specific context to reduce hallucination.

Source of truth: docs/ontology.md and docs/agent-swarms.md
Update these constants when the docs change.
"""

# ── Shared Domain Context (~200 tokens) ────────────────────────────────
DOMAIN_CONTEXT = """
TCGNakama is a Japan-based marketplace for Pokémon, One Piece, Magic: The Gathering,
and Yu-Gi-Oh! single cards. All prices are in JPY. Cards have: title (Japanese + English),
set code (e.g. SV5M, OP12), full set name, card number, rarity tier
(Common/Uncommon/Rare/Epic/Ultra Rare), condition (Near Mint/Lightly Played/Moderately Played/
Heavily Played/Damaged), and package type (Raw/Toploader/Booster Pack/Slab).
"""

# ── Role-Specific Context ──────────────────────────────────────────────

APPRAISAL_CONTEXT = """
Rarity mapping: C/common→Common, UC/uncommon→Uncommon, R/rare/holo rare→Rare,
super rare→Epic, SR/SAR/SEC/UR/HR/mythic rare/prism/crystal/shining→Ultra Rare.
Card number formats: ###/### (modern), P-### (One Piece promo), ###/P (Pokémon promo).
Set codes: Japanese modern sets use alphanumeric codes (SV5M, sA, s10b).
One Piece uses OP## prefix. Single regulation letters (D/E/F/G/H) are NOT set names.
"""

BLOG_CONTEXT = """
TCGNakama runs 9 autonomous agents including: Card Vision Appraisal (Gemini vision for
card identification), Market Value Estimator (PriceCharting + Gemini), Blog Generator (this agent),
Price Tracker (batch PriceCharting updates), and Showcase Video Pipeline (Gemini + Pollo AI).
The marketplace features: Fresh Pulls (new listings), What's Hot (price gainers),
collection filtering, and individual card detail pages with market value comparison.
"""

PRICE_CONTEXT = """
PriceCharting returns product names that may include variants like [Ichiban Kuji], [Alt Art],
[Promo], [Parallel], [Serial]. Regular (non-variant) versions are preferred for market value.
English versions preferred over Japanese. Card numbers may appear as #1, #001, #001/024,
OP13-001. When matching: card number > regular version > English > card name.
"""

DESIGN_CONTEXT = """
TCGNakama uses a "Vault Terminal" dark luxury aesthetic:
- Background: #0B1120 (deep navy-black). Surfaces: #111827. Borders: white/10 opacity.
- Primary color: #FFD700 (gold) for CTAs, active states, prices, and badges.
- Accents: #EF4444 (neon-red for sold-out/danger), #22C55E (neon-green for in-stock/success).
- Font: Space Grotesk (400, 600). Icons: Material Symbols Outlined.
- Effects: glassmorphism (backdrop-blur + translucent backgrounds), holographic gold glows.
- Component style: rounded-xl cards with faint borders, rounded-full CTAs and pills,
  uppercase 10px labels with wide tracking, minimal shadows.
- Interaction: HTMX for search/filter, Fetch API for cart, CSS transitions for hover.
- Admin panel is the exception — uses light #f3f4f6 background (utility mode).
- Tone: premium, collector-focused, confident but not aggressive. Mix of 🔥 and 🃏 energy.
"""


def get_context(role: str) -> str:
    """Return grounding context string for a given agent role.

    Args:
        role: One of 'appraisal', 'set_resolver', 'blog', 'price_filter',
              'price_tracker', 'showcase', 'ui'. Unknown roles get DOMAIN_CONTEXT.
    """
    role_map = {
        "appraisal": DOMAIN_CONTEXT + APPRAISAL_CONTEXT,
        "set_resolver": DOMAIN_CONTEXT + APPRAISAL_CONTEXT,
        "blog": DOMAIN_CONTEXT + BLOG_CONTEXT + DESIGN_CONTEXT,
        "price_filter": DOMAIN_CONTEXT + PRICE_CONTEXT,
        "price_tracker": DOMAIN_CONTEXT + PRICE_CONTEXT,
        "showcase": DOMAIN_CONTEXT,
        "ui": DOMAIN_CONTEXT + DESIGN_CONTEXT,
    }
    return role_map.get(role, DOMAIN_CONTEXT)
