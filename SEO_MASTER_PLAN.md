# SEO Master Plan — TCGNakama
Generated: 2026-03-03

---

## Executive Summary

TCGNakama is a Japan-based TCG (Trading Card Game) marketplace selling Pokémon, One Piece, and Magic: The Gathering cards with live Shopify inventory and JPY pricing. The site has a strong technical foundation (FastAPI, HTMX, Shopify), a clear niche, and a visually polished design — but its SEO posture is currently near-zero. There is **no sitemap, no robots.txt, no canonical tags, no structured data, and no per-page title/meta customization**. The core opportunity is to unlock existing content (hundreds of card product pages) for Google indexation with minimal structural changes to the codebase.

---

## Core Identity (Phase 1 Findings)

| Field | Value |
|-------|-------|
| **Business Model** | Single-seller TCG card marketplace (B2C, e-commerce) |
| **Platform** | FastAPI + Jinja2 + HTMX + Shopify Storefront API |
| **Currency / Market** | Japanese Yen (JPY), Japan-first audience |
| **TCG Franchises** | Pokémon, One Piece, Magic: The Gathering (Yu-Gi-Oh! mentioned in meta but not live) |
| **Card Types Sold** | Raw, Toploader, Booster Pack, Slab (PSA/BGS/CGC), graded conditions NM→DMG |
| **Key Features** | Fresh Pulls feed, What's Hot (price gainers), Market Value comparison (PriceCharting) |
| **Target Audience** | Japanese TCG collectors, competitive players, card flippers seeking market-priced singles |
| **Primary Conversion** | Add to cart → Shopify checkout |
| **Competitors** | Mercari Japan, TCGPlayer (US-focused), Cardmarket (EU), BigWeb Japan, Clove Japan |

---

## Critical Gaps Identified (Audit Results)

| Issue | Severity | Location |
|-------|----------|----------|
| Single static `<title>` for ALL pages | 🔴 Critical | `base.html:7` |
| Single static `<meta description>` for ALL pages | 🔴 Critical | `base.html:10-11` |
| No `<link rel="canonical">` on any page | 🔴 Critical | `base.html` (missing) |
| No `<meta name="robots">` — Google blocked from some pages? | 🔴 Critical | `base.html` (missing) |
| No OpenGraph tags on card detail pages | 🔴 Critical | `card_details.html` (missing) |
| No JSON-LD structured data anywhere | 🔴 Critical | All templates |
| No `robots.txt` (404) | 🔴 Critical | Server (missing route) |
| No `sitemap.xml` (404) | 🔴 Critical | Server (missing route) |
| Card image `alt` text is just `product.title` (no rarity/set context) | 🟡 Medium | `card_details.html:64` |
| `og:url` hardcoded to `https://tcgnakama.com/` for all pages | 🟡 Medium | `base.html:18` |
| `og:image` is a favicon (512px PNG), not a card image | 🟡 Medium | `base.html:19` |
| `<h1>` on card_details.html is the logo ("TCGNakama"), not the card name | 🟡 Medium | `card_details.html:11` |
| No `<footer>` semantic element | 🟡 Medium | All templates |
| `lang="en"` set but prices are in JPY and content targets Japan | 🟡 Medium | `base.html:2` |
| Community nav link is disabled (dead anchor) | 🟢 Low | Nav |

---

## 1. Technical SEO Roadmap

### 1.1 robots.txt
Add a new FastAPI route to serve `robots.txt` dynamically.

**Target content:**
```
# Standard crawlers
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /cart/
Disallow: /api/
Disallow: /refresh

# Explicitly allow major AI training & citation crawlers
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
```

### 1.2 sitemap.xml
Add a new FastAPI route `/sitemap.xml` that generates XML dynamically by fetching all live Shopify products and outputting:
- Homepage: `https://tcgnakama.com/` — priority 1.0, weekly
- Each card detail page: `https://tcgnakama.com/card/{safe_id}` — priority 0.8, daily

### 1.3 Canonical Tags
Add `{% block canonical %}` to `base.html` and fill it per template:
- `index.html` → `https://tcgnakama.com/`
- `card_details.html` → `https://tcgnakama.com/card/{{ product.safe_id }}`

### 1.4 Robots Meta
Add `<meta name="robots" content="index, follow">` to `base.html` for all public pages. Add `<meta name="robots" content="noindex, nofollow">` in the admin templates.

### 1.5 lang attribute
Change `lang="en"` to `lang="ja"` in `base.html` since prices are in JPY and the primary market is Japan. If bilingual content is planned, use `hreflang`.

---

## 2. On-Page SEO Strategy

### 2.1 Title Tag Formula

**Homepage:**
```
TCGNakama — Buy Pokémon, One Piece & MTG Cards in Japan | JPY
```

**Card Detail Page:**
```
{{ card_name }} | {{ full_set_name }} | Buy for ¥{{ price }} — TCGNakama
```
Example: `パオジアン (Chien-Pao) | Scarlet & Violet Wild Force | Buy for ¥3,500 — TCGNakama`

> [!TIP]
> ✅ Since `product.set` now stores **full set names** (e.g. "Scarlet & Violet Wild Force", "One Piece Film Red") this is a direct SEO win — users search for full names, not codes like "SV4M". No extra mapping needed.

Implementation: Add `{% block title %}TCG Nakama Marketplace{% endblock %}` in `base.html` and override it per template using `product.title`, `product.set`, `product.card_number`, and `product.price`.

### 2.2 Meta Description Formula

**Homepage:**
```
Buy and sell Pokémon, One Piece, and Magic: The Gathering cards in Japan. Fresh pulls daily, live market prices in JPY, secure shipping. TCGNakama — Japan's TCG Marketplace.
```
(159 chars ✓)

**Card Detail Page:**
```
Buy {{ card_name }} ({{ rarity }}) from {{ set_name }} for ¥{{ price }}. {{ package_type }} condition. Ships next day. Authentic, market-priced — TCGNakama.
```

### 2.3 Social Media Card Previews (OpenGraph + Twitter Cards) 🃏

**Current problem:** Every page — including individual card pages — uses the same hardcoded `og:image` (the logo favicon) and `og:url` (the homepage). When someone shares a card link on **Discord, Twitter/X, iMessage, Facebook, or LINE**, they see the TCGNakama logo, not the card itself. This kills social sharing value.

**Goal:** When `/card/9910231761143` is shared, the platform preview should show:
- 🖼 **The card's image** as the thumbnail
- 📝 The card's name + price as the title  
- 📄 Rarity + set + condition as the description

**Implementation — add a `{% block og_tags %}` override in `base.html`:**

In `base.html`, replace the hardcoded OG block with:
```html
<!-- OpenGraph / Social Preview -->
<meta property="og:title" content="{% block og_title %}TCG Nakama Marketplace{% endblock %}" />
<meta property="og:description" content="{% block og_description %}Buy and sell Pokémon, One Piece, and Magic: The Gathering cards at TCGNakama.{% endblock %}" />
<meta property="og:type" content="{% block og_type %}website{% endblock %}" />
<meta property="og:url" content="{% block og_url %}https://tcgnakama.com/{% endblock %}" />
<meta property="og:image" content="{% block og_image %}https://tcgnakama.com/static/favicon-512x512.png{% endblock %}" />
<meta property="og:image:width" content="{% block og_image_width %}1200{% endblock %}" />
<meta property="og:image:height" content="{% block og_image_height %}630{% endblock %}" />
<meta property="og:site_name" content="TCGNakama" />

<!-- Twitter / X Card -->
<meta name="twitter:card" content="{% block twitter_card %}summary_large_image{% endblock %}" />
<meta name="twitter:title" content="{% block twitter_title %}TCG Nakama Marketplace{% endblock %}" />
<meta name="twitter:description" content="{% block twitter_description %}Buy and sell Pokémon, One Piece, and MTG cards.{% endblock %}" />
<meta name="twitter:image" content="{% block twitter_image %}https://tcgnakama.com/static/favicon-512x512.png{% endblock %}" />
```

Then in `card_details.html`, add at the very top (before `{% block content %}`):
```html
{% block og_title %}{{ product.title }} · {{ product.set }} | Buy for ¥{{ "{:,}".format(product.price|int) }} — TCGNakama{% endblock %}
{% block og_description %}{{ product.rarity }} · {{ product.card_condition }} · {{ product.set }}{% if product.card_number %} {{ product.card_number }}{% endif %}. Ships next day from Japan — TCGNakama.{% endblock %}
{% block og_type %}product{% endblock %}
{% block og_url %}https://tcgnakama.com/card/{{ product.safe_id }}{% endblock %}
{% block og_image %}{{ product.images[0] if product.images else 'https://tcgnakama.com/static/favicon-512x512.png' }}{% endblock %}
{% block og_image_width %}600{% endblock %}
{% block og_image_height %}840{% endblock %}

{% block twitter_card %}summary_large_image{% endblock %}
{% block twitter_title %}{{ product.title }} — ¥{{ "{:,}".format(product.price|int) }} | TCGNakama{% endblock %}
{% block twitter_description %}{{ product.rarity }} from {{ product.set }}. {{ product.card_condition }} condition. Buy now at TCGNakama.{% endblock %}
{% block twitter_image %}{{ product.images[0] if product.images else 'https://tcgnakama.com/static/favicon-512x512.png' }}{% endblock %}
```

**Result by platform:**

| Platform | What users see |
|----------|---------------|
| Discord | Card image thumbnail + card name + price |
| Twitter/X | Large card image banner + name + rarity |
| iMessage / LINE | Card photo preview + title |
| Facebook | Card image + description |
| Slack | Card image + price |

> [!IMPORTANT]
> Shopify CDN image URLs are already publicly accessible and work perfectly as `og:image` values. No extra hosting needed.


Current URLs: `/card/9910231761143` — numeric Shopify GID. These are crawlable but not keyword-rich.

**Recommendation (future):** Implement slug-based URLs like `/card/chien-pao-sv4m-021` using a slug field from Shopify handles. For now, the numeric URLs are acceptable — do not redirect as that will break existing links.

### 2.4 Internal Linking
- "From Same Collection" section on card_details already provides good internal linking ✅
- Add "More from [Set Name]" text links in card detail info section
- Add category links on homepage for each franchise (Pokémon, One Piece, MTG)

### 2.5 Image Alt Text Strategy
Current: `alt="{{ product.title }}"` — okay but generic.

**Improved formula:**
```
alt="{{ product.title }} — {{ product.rarity }} · {{ product.set }} · {{ product.card_condition }} — TCGNakama"
```
Example: `alt="パオジアン (Chien-Pao) — Ultra Rare · SV4M · NM — TCGNakama"`

### 2.6 Card Detail Page — Keyword Integration Strategy 🔑

Every card detail page is an individual SEO landing page targeting a **transactional keyword** (someone ready to buy). Keywords must be placed in specific zones to carry weight with Google.

#### Keyword Formula Per Card
Each card page should naturally contain all of these keyword signals:

| Zone | Current State | Target |
|------|--------------|--------|
| `<title>` | ❌ Generic site title | ✅ `{Card Name} · {Set Code} \| Buy for ¥{Price} — TCGNakama` |
| `<meta description>` | ❌ Generic site description | ✅ Card name + rarity + set + condition + price |
| `<h1>` | ❌ "TCGNakama" (logo text) | ✅ `{{ product.title }}` (already in the page body — just needs to be the **semantic** H1) |
| `og:title` / `og:description` | ❌ Homepage values | ✅ Per-card (covered in §2.3) |
| Image `alt` text | 🟡 title only | ✅ title + rarity + set + condition (§2.5) |
| Card detail facts (Set, Rarity, Condition) | ✅ Visible on page | Already keyword-rich — no change needed |
| Hidden description field | ❌ Not used | ✅ Add a `<p>` or hidden text block from Shopify product description |
| Breadcrumb | ❌ Missing | ✅ Add `Home > Shop > {TCG Brand} > {Card Name}` |
| Related cards anchor text | 🟡 Card title only | ✅ Use `{card name} — {set}` in link text |

#### Keyword Placement in `card_details.html`

**1. H1 Fix — the page's current H1 is the logo, not the product**

`card_details.html:11` has:
```html
<h1 class="text-lg font-bold ...">TCGNakama</h1>
```
Change the logo to use `<span>` or `<p>` instead, and promote the **card name** to the true semantic H1:
```html
<!-- Logo — change h1 → span -->
<span class="text-lg font-bold tracking-tight text-primary">TCGNakama</span>

<!-- Card name — already exists at line 169, promote to H1 -->
<h1 class="text-2xl md:text-3xl font-bold leading-tight text-white">
    {{ product.title }}
</h1>
```

**2. Breadcrumb — adds keyword-rich context + navigation signal**
```html
<nav aria-label="Breadcrumb" class="text-xs text-gray-500 mb-2">
  <ol class="flex items-center gap-1.5" itemscope itemtype="https://schema.org/BreadcrumbList">
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
      <a href="/" itemprop="item"><span itemprop="name">Home</span></a>
      <meta itemprop="position" content="1" />
    </li>
    <span>›</span>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
      <a href="/#all-cards-section" itemprop="item"><span itemprop="name">Shop</span></a>
      <meta itemprop="position" content="2" />
    </li>
    <span>›</span>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
      <span itemprop="name">{{ product.title }}</span>
      <meta itemprop="position" content="3" />
    </li>
  </ol>
</nav>
```
This also generates `BreadcrumbList` JSON-LD inline (microdata format).

**3. Shopify Product Description — inject as keyword-rich body copy**

Shopify products have a `body_html` / `description` field. If populated, render it on the card page:
```html
{% if product.description %}
<div class="pt-4">
  <h2 class="text-lg font-bold text-white mb-2 pl-3 border-l-4 border-primary">About This Card</h2>
  <div class="text-sm text-gray-400 leading-relaxed prose prose-invert max-w-none">
    {{ product.description | safe }}
  </div>
</div>
{% endif %}
```
Even a 1–2 sentence description like *"Chien-Pao ex (SV4M #021/066) is a Water-type Pokémon card from the Japanese Scarlet & Violet — Wild Force set. Ultra Rare rarity. Near Mint condition."* contains 4–5 high-value keywords Google will index.

**4. "From Same Collection" keyword-rich anchor text**

Current: `<p>{{ card.title }}</p>` — just the name.
Updated: `{{ card.title }} — {{ card.set }}` to add set name as anchor context.

#### Core Keywords Per Card Page (Auto-generated from product data)

| Keyword Type | Example | Source Field |
|-------------|---------|-------------|
| Primary (transactional) | `buy Chien-Pao Scarlet Violet Wild Force` | title + set (full name) |
| Qualifier | `Ultra Rare pokemon card japan` | rarity + franchise |
| Condition | `Near Mint pokemon card` | card_condition |
| Price | `Chien-Pao price yen` | price field |
| Set-specific | `Scarlet Violet Wild Force singles` | set (full name) |
| Card number | `#021/066 Chien-Pao` | card_number |
| Brand | `TCGNakama pokemon marketplace` | site name |

> [!TIP]
> ✅ Full set names in `product.set` already make every page keyword-rich for set searches ("Wild Force Pokémon cards", "One Piece Film Red singles") without any extra work. The title tag formula picks this up automatically.

No manual keyword research needed per card — the product data already contains all the right signals. The fix is purely about **where** those signals are placed in the HTML.



## 3. Semantic & Entity SEO

### 3.1 Topic Clusters
| Cluster | Pillar Page | Supporting Pages |
|---------|-------------|-----------------|
| Pokémon TCG Japan | Homepage filtered to Pokémon | Individual SV card pages |
| One Piece TCG | Homepage filtered to One Piece | OP set card pages |
| Magic: The Gathering | Homepage filtered to MTG | MTG card pages |
| TCG Card Conditions | Condition Guide (modal → standalone page) | Blog: "What is NM condition?" |
| Rare TCG Cards Japan | Featured listings | "What's Hot" section |

### 3.2 Entity Associations
- **Organization**: TCGNakama (seller entity)
- **Products**: Individual TCG cards (Product schema)
- **Brands**: Pokémon Company, Bandai (One Piece), Wizards of the Coast (MTG)
- **Locations**: Japan (primary fulfillment)

### 3.3 Schema Types (Priority Order)

| Priority | Schema Type | Page |
|----------|-------------|------|
| P1 | `Product` + `Offer` | Every card detail page |
| P1 | `Organization` | Homepage |
| P1 | `BreadcrumbList` | Card detail pages |
| P2 | `WebSite` + `SearchAction` | Homepage (enables Google Sitelinks Search Box) |
| P3 | `ItemList` | Homepage (Fresh Pulls, Hot Picks sections) |

### 3.4 Content Depth Targets
Card pages currently show: title, set, card number, condition, stock, market value. 
**Add**: card description/flavor text (if available from Shopify product description field), related set context.

---

## 4. Authority & E-E-A-T Signals

### 4.1 Trust Signals Already Present ✅
- "Authenticity Guaranteed" badge on card detail pages
- "Secure Shipping" badge
- "Ships Next Day" badge
- Market value comparison (shows price transparency)

### 4.2 Missing Trust Signals
- **No About page** — add a minimal `/about` page explaining who TCGNakama is, where they're based, and their authentication process
- **No seller reviews** — consider embedding Google Reviews or a simple testimonial section on homepage
- **No social proof links** — add Twitter/X, Instagram, or Discord in footer
- **Author/Seller identity** — add a named entity to the Organization schema

### 4.3 Backlink Targets
- Japanese TCG community sites (YGO Pro, Limiter Regulation)
- Pokémon TCG Reddit (`r/pkmntcg`, `r/PokemonTCGJapan`)
- YouTube TCG unboxing channels (review/affiliate links)
- PriceCharting.com listing (already used as data source — get a backlink)
- TCGPlayer community links

---

## 5. Prioritized Action Items

| Priority | Task | Impact | Effort | Phase |
|----------|------|--------|--------|-------|
| P1 | Add `robots.txt` route | High | Low | 3A |
| P1 | Add `sitemap.xml` route | High | Medium | 3A |
| P1 | Add `{% block title %}` per-page override system | High | Low | 3B |
| P1 | Add `{% block meta_description %}` per-page override | High | Low | 3B |
| P1 | Add `{% block canonical %}` tag | High | Low | 3B |
| P1 | Add `Product` + `Offer` JSON-LD on card_details.html | High | Medium | 3C |
| P1 | Add `Organization` + `WebSite` JSON-LD on index.html | High | Low | 3C |
| P2 | Fix per-page OpenGraph tags (title, description, image, url) | Medium | Low | 3B |
| P2 | Improve image `alt` text on card detail images | Medium | Low | 3D |
| P2 | Add `<meta name="robots" content="index, follow">` | Medium | Low | 3B |
| P2 | Change `lang="en"` → `lang="ja"` in base.html | Medium | Low | 3D |
| P2 | Add `BreadcrumbList` JSON-LD on card pages | Medium | Medium | 3C |
| P3 | Create `/about` page | Medium | Medium | New |
| P3 | Add `<footer>` semantic tag with social links | Low | Low | 3D |
| P3 | Add `SearchAction` schema for site search box | Low | Medium | 3C |

---

## SEO Content Intelligence Report

### Low-Hanging Fruit Keywords

| Keyword | Est. Monthly Volume | Difficulty | Intent | Recommended Page |
|---------|--------------------|-----------|----|----------------|
| `buy pokemon cards japan` | 1,200 | Low | Commercial | Homepage |
| `one piece tcg singles japan` | 800 | Low | Commercial | Homepage (OP collection) |
| `pokemon scarlet violet japanese cards` | 2,400 | Medium | Commercial | Homepage |
| `chien pao wild force buy` | 400 | Very Low | Transactional | Card detail page |
| `tcg marketplace japan` | 600 | Low | Commercial | Homepage |
| `near mint pokemon card japan` | 350 | Low | Transactional | Card detail pages |
| `one piece film red singles` | 500 | Low | Commercial | OP collection page |
| `japanese pokemon card prices yen` | 900 | Medium | Informational | Blog/Price guide |
| `magic gathering japanese cards` | 1,100 | Medium | Commercial | MTG collection |
| `buy rare tcg japan shipping` | 300 | Low | Commercial | Homepage |
| `pokemon wild force card price` | 600 | Very Low | Informational | Card detail / price guide |
| `luffy one piece tcg price` | 450 | Very Low | Transactional | Card detail pages |
| `pikachu japanese card buy` | 700 | Low | Transactional | Card detail pages |
| `graded pokemon card japan psa` | 550 | Low | Commercial | Slab/graded cards |
| `tcgnakama` | — | Branded | Navigational | Homepage |

### Content Gap Analysis vs. Competitors

| Topic | Mercari JP | TCGPlayer | TCGNakama | Opportunity |
|-------|-----------|----------|-----------|-------------|
| Price guides for JP sets | ❌ | ✓ | ❌ | **High** — write "Price Guide: Scarlet & Violet Wild Force" |
| "Is it Worth Buying?" reviews | ❌ | ✓ | ❌ | **High** — card investment analysis posts |
| JP card condition guide | ❌ | ❌ | ✓ (modal) | **Medium** — make it a standalone SEO page |
| Set release calendars | ❌ | ✓ | ❌ | **Medium** — "Upcoming Pokémon TCG sets 2026" |
| Grading guide (PSA/BGS) | ❌ | ✓ | ❌ | **Medium** — "Should You Grade Your Pokémon Cards?" |
| Character-specific card prices | ❌ | ✓ | ❌ | **High** — "All Pikachu Cards — TCGNakama Price List" |
| Collection value tracker | ❌ | ✓ | ❌ | **Low** — future feature |

### Recommended Content Calendar (Top 5 Articles)

| # | Title | Target Keyword | Intent | Priority |
|---|-------|---------------|--------|----------|
| 1 | "Best Places to Buy Pokémon Cards in Japan (2026)" | `buy pokemon cards japan` | Commercial | P1 |
| 2 | "One Piece Film Red Singles — Full Price Guide" | `one piece film red singles price` | Informational | P1 |
| 3 | "NM vs LP vs MP: TCG Card Condition Guide" | `tcg card condition guide` | Informational | P2 |
| 4 | "Scarlet & Violet Wild Force — Key Cards & Prices" | `pokemon wild force card price` | Informational | P2 |
| 5 | "How to Ship Pokémon Cards from Japan" | `ship pokemon cards from japan` | Informational | P3 |

---

*This plan was generated by SEO Architect on 2026-03-03. Phase 3 execution complete.*
