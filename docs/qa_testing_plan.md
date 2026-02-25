# TCG Nakama — QA Testing Plan (ISTQB-Lite)

## Test Environment

| Key | Value |
|-----|-------|
| **Local** | http://localhost:8001 |
| **Production** | https://tcgnakama.com |
| **Credentials** | admin@asistee.com / nakama2026 |
| **Browser** | Chrome 120+ (desktop + DevTools mobile) |
| **Mobile viewport** | 390×844 (iPhone 14) |

### Priority Definitions

| Level | Meaning | When to run |
|-------|---------|-------------|
| **P1** | Revenue / data-blocking if broken | Every deploy |
| **P2** | Core functionality | Every feature (`/qa-test`) |
| **P3** | Secondary features | Weekly / milestone |
| **P4** | Cosmetic / edge cases | Before major release |

---

## 1. Public Marketplace (/)

> **Precondition:** Server running on port 8001, Shopify products synced (50+ products), at least 1 active banner uploaded.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Page loads | Navigate to `/` | Products display within 3s, no console errors | ✅ |
| P1 | Add to cart | Click "Add to Cart" on in-stock card | Cart count increments by 1, drawer opens | ✅ |
| P1 | Cart persists | Add item → refresh page | Cart items remain (Shopify cart ID preserved) | ✅ |
| P2 | Search works | Type "Pikachu" in search | ≥1 Pokémon card with "Pikachu" in title appears | ✅ |
| P2 | Search tracking | Search "Mewtwo" | Analytics → Trending Searches shows "Mewtwo" | ✅ |
| P2 | Product modal | Click any product card | Modal opens with title, image, price, stock status | ✅ |
| P2 | Rarity filter | Click "Rare" rarity button | Only cards tagged `rarity:Rare` display | ✅ |
| P2 | Collection filter | Click "ONE PIECE" tab | Only One Piece cards display with correct stock | ✅ |
| P3 | Banner carousel | View homepage, wait 10s | Banners auto-rotate every 5s, dots update | ✅ |
| P3 | Banner swipe | Swipe banner on mobile (390px) | Carousel advances on touch swipe | ☐ |
| P3 | Responsive | Resize to 390px width | Layout adapts, no horizontal overflow | ✅ |

---

## 1a. Add to Cart Button (CardComponent QA)

> **Precondition:** At least 1 in-stock product visible in grid.

### Event Listener Binding

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Grid button fires | Click "Add" on any grid card | `handleCartAction()` executes, no JS errors in console | ✅ |
| P1 | Modal button fires | Open modal → click cart icon | `handleCartAction()` fires with quantity value | ✅ |
| P2 | No stale HTMX attrs | Inspect grid button DOM | No `hx-post`, `hx-target`, or `hx-swap` attributes | ✅ |
| P3 | All card types work | Test OP10, OP13, Pokémon cards | Same button behavior across all collections | ✅ |

### Mobile vs Desktop Tap Targets

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P2 | Mobile tap (375px) | Tap Add on mobile viewport | Button responds on first tap, no double-tap needed | ✅ |
| P2 | Desktop click (1280px) | Click Add on desktop viewport | Button responds on first click | ✅ |
| P4 | Button height ≥ 36px | Inspect button computed styles | `min-height: 36px` (meets Apple HIG guideline) | ✅ |
| P2 | No accidental modal open | Click Add button only | Only cart action fires, modal does NOT open | ✅ |

### Success Feedback

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Header badge updates | Click Add | `#cart-count` increments by 1 | ✅ |
| P2 | Green checkmark | Click Add → wait | Green `check_circle` icon appears for 2s | ✅ |
| P2 | Button reverts | Wait 2s after checkmark | Original "🛒 Add" content restores | ✅ |
| P2 | Mobile badge updates | Click Add on mobile | `#cart-count-mobile` increments in sync | ✅ |
| P2 | Double-click protection | Rapid double-click Add | Button gets `pointer-events-none` during request | ✅ |

### Z-Index / Overlay Audit

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | No overlay blocking | Click Add in grid footer | Click registers (no invisible layer above button) | ✅ |
| P3 | Card image doesn't cover button | Inspect card layout | Image container ends before info/action area | ✅ |
| P2 | Modal backdrop doesn't leak | Close modal → click grid Add | Button clickable immediately after modal dismissed | ✅ |

### Error Handling

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P2 | Network error | Disconnect Wi-Fi → click Add | Red `error` icon shows for 2s, badge does not increment | ☐ |
| P4 | Invalid variant | Corrupt `variant_id` in DOM | Error state shown, no JS crash | ☐ |

---

## 1b. Collection Filter — Inventory Accuracy (Regression)

> [!IMPORTANT]
> **Precondition:** Server running, products synced. Fix ref: commit `69198dd` — ghost sold-out bug.

### Stock Status After Filter

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | No filter (baseline) | Load `/` → scroll to All Cards | In-stock items show "In Stock" badge + active ADD button | ✅ |
| P1 | ONE PIECE filter | Click ONE PIECE collection tab | In-stock OP cards show "In Stock", `totalInventory > 0` | ✅ |
| P1 | POKEMON filter | Click Pokemon collection tab | In-stock Pokémon cards show "In Stock", `totalInventory > 0` | ✅ |
| P2 | YU-GI-OH filter | Click Yu-Gi-Oh! collection tab | In-stock cards show "In Stock" | ☐ |
| P2 | MAGIC: TG filter | Click Magic: TG collection tab | In-stock cards show "In Stock" | ☐ |
| P2 | Filter → unfilter | Select collection → click CLEAR | All cards restore correct stock status | ☐ |
| P2 | Filter switching | ONE PIECE → POKEMON → ONE PIECE | Stock status stays correct across all switches | ✅ |

### Inventory Count Accuracy

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Detail page stock | Filter → click card → view details | Shows "X available" matching Shopify admin inventory | ✅ |
| P1 | Add to Cart enabled | Filter → click in-stock card | "Add to Cart" button is active (not disabled/greyed) | ✅ |
| P2 | Sold out card (real) | Find truly sold-out product | "SOLD OUT" overlay displayed, ADD button disabled | ☐ |
| P2 | RESYNC after filter | Filter → RESYNC → filter again | Stock status remains accurate post-sync | ✅ |

### Technical Guardrails

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Multi-variant product | Product with 2+ variants, variant 1 OOS | Card shows "In Stock" if ANY variant `availableForSale` | ✅ |
| P2 | totalInventory field | Check server response after filter | `totalInventory > 0` for all in-stock products | ✅ |

---

## 2. Authentication (/admin/login)

> **Precondition:** Not logged in. Valid credentials: admin@asistee.com / nakama2026.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Login page loads | Go to `/admin/login` | Styled login form with email + password fields | ✅ |
| P1 | Valid login | Enter correct credentials → submit | Redirects to `/admin` within 2s | ✅ |
| P1 | Invalid login | Enter wrong password → submit | Error message shown, no redirect | ☐ |
| P2 | Session persists | Login → refresh page | Still logged in (session cookie valid) | ☐ |
| P2 | Logout works | Click Logout button | Redirects to `/`, no browser popup | ☐ |
| P2 | Session cleared | Logout → navigate to `/admin` | Redirects to `/admin/login` | ☐ |
| P3 | Merchant link | Click footer "Merchant Login" | Navigates to `/admin/login` | ☐ |

---

## 3. Admin Dashboard (/admin)

> **Precondition:** Logged in as admin. Shopify connected (green badge).

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Dashboard loads | Login → view dashboard | Products list with images, prices, status badges | ✅ |
| P1 | Shopify status | Check header badge | Shows "Shopify Connected" (green) | ✅ |
| P2 | Search products | Type card name in vault search | Products list filters to matching results | ✅ |
| P2 | Sync button | Click Sync Shopify | Products refresh from Shopify, count updates | ☐ |
| P2 | Pagination | Click NEXT → PREV | Products paginate, page indicator updates correctly | ✅ |
| P3 | Set buy price | Click product → enter ¥ price | Price saves, profit column calculates | ☐ |
| P3 | Set grade | Select grade (S/A/B/C) | Grade saves and displays | ☐ |
| P3 | Days in vault | Check product cards | Shows days since `createdAt` | ☐ |
| P3 | Filter pills | Toggle STOCK/AGE/VALUE/COST/SELL/G\/L/GRADE | Columns show/hide correctly | ☐ |

### 3a. Active Leaderboard

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P3 | Leaderboard renders | View dashboard | Horizontal scrollable rank cards visible | ✅ |
| P4 | Top 3 styling | Check ranks 1-3 | Gold (#1), Silver (#2), Bronze (#3) border colors | ✅ |
| P4 | Shows 10 ranks | Scroll leaderboard | 10 rank cards with flag, username, LTV | ✅ |
| P3 | Horizontal scroll | Swipe/drag on mobile | Cards scroll left-right, no vertical jump | ✅ |

### 3b. Inventory Value Chart

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P2 | Chart renders | View "Obsidian Sales Hub" section | Chart.js line chart appears with data points | ✅ |
| P2 | Total value display | Check value heading | Shows ¥ total (e.g., ¥20,574) | ✅ |
| P3 | W-o-W indicator | Check below total value | Shows "↑ +X.X% vs last week" or "↓ −X.X%" | ✅ |
| P3 | Historical data | Check chart X-axis | Shows weekly labels (W04, W05, W06, W07) | ✅ |
| P4 | Teal gradient fill | Visual check | Area under line has teal gradient fill | ✅ |
| P4 | Tooltip on hover | Hover a data point | Dark tooltip shows ¥ value | ☐ |
| P2 | Weekly snapshot | Reload dashboard | New snapshot saved to DB (check server logs) | ✅ |
| P3 | Snapshot dedup | Reload multiple times in same week | Only one snapshot per week, updates if changed | ☐ |

---

## 4. Add Card (/admin/add-card)

> **Precondition:** Logged in as admin. Shopify connected.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Page loads | Navigate to Add Card | Form with title, price, images, collections, stock fields | ✅ |
| P1 | Submit card | Fill all fields → submit | Loading overlay → card created in Shopify within 5s | ☐ |
| P2 | Image upload | Upload a local JPG/PNG file | Preview thumbnail appears in image strip | ☐ |
| P2 | Image URL | Paste image URL | Preview thumbnail appears | ☐ |
| P2 | Required fields | Submit empty form | Validation errors on title + price | ☐ |
| P2 | Stock stepper | Click +/− buttons | Value increments/decrements (min: 1, max: 99) | ✅ |
| P3 | Multiple images | Add 3+ images | All previews in horizontal scroll strip | ☐ |
| P3 | Collection select | Check/uncheck collections | At least one required to submit | ☐ |
| P3 | Edit mode | Edit existing card | Pre-fills all fields including images | ☐ |
| P4 | Footer nav | Check bottom nav | 4 buttons, no "SOON" badge on Settings | ✅ |

---

## 5. Analytics (/admin/analytics)

> **Precondition:** Logged in as admin. At least 1 search performed, products synced.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P2 | Page loads | Navigate to Analytics | All sections render within 3s | ✅ |
| P2 | PSA 10 candidates | View grading section | Top candidates with % scores displayed | ✅ |
| P2 | Trending searches | View searches section | Recent user search terms listed | ✅ |
| P3 | Customer countries | View countries section | Order countries show (or "No data" if no orders) | ✅ |
| P3 | Top spenders | View spenders section | Customer totals show (or "No data") | ✅ |
| P4 | Bundle recommendations | View bundles section | Product pairs show (or "No data") | ☐ |

---

## 6. Banner Management (/admin/settings)

> **Precondition:** Logged in as admin.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P2 | Settings page loads | Click Settings in footer | Banner list with thumbnails displays | ✅ |
| P2 | Upload banner | Click + → select 1920×480 image | Banner created, shown in list immediately | ✅ |
| P2 | Delete banner | Click Delete → confirm dialog | Banner removed from list and homepage carousel | ✅ |
| P2 | Toggle active/inactive | Click toggle icon | Status changes, homepage carousel updates | ✅ |
| P3 | Edit banner | Click Edit → change title | Title updates correctly | ✅ |
| P3 | Banner on homepage | Upload new banner → visit `/` | New banner appears in carousel | ✅ |
| P3 | Image file serving | Check all banner images | All images display (no broken icons) | ✅ |
| P4 | Dimension guidance | View upload form | Shows recommended 1920×480px guidance | ✅ |
| P4 | Max file size | Upload 20MB+ image | Graceful error or auto-resize | ☐ |

---

## 7. Shopify Integration

> **Precondition:** Valid Shopify Storefront API token available.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Products sync | Dashboard → Sync Shopify | Products refresh, count matches Shopify admin | ✅ |
| P1 | Valid token | Enter valid `shpat_` token → submit | Saves to `.env`, shows "Connected" success | ✅ |
| P2 | Manual token page | Navigate to `/admin/connect-shopify` | Token entry form with instructions appears | ✅ |
| P2 | Invalid token | Enter "bad_token" → submit | Error: "must start with shpat_" | ✅ |
| P2 | Dashboard link | Click "Reconnect Shopify" on dashboard | Navigates to `/admin/connect-shopify` | ✅ |
| P3 | Token validation | Enter `shpat_` + random chars | Tests against Shopify API, shows "invalid" error | ☐ |
| P3 | Order data | Check Analytics page | Countries/spenders populated from Shopify orders | ✅ |

---

## 8. Footer Navigation Consistency

> **Precondition:** Logged in as admin.

| Pri | Test Case | Page | Expected Buttons | Pass/Fail |
|-----|-----------|------|------------------|-----------| 
| P2 | Dashboard footer | `/admin` | Vault · Add Card · Analytics · Settings | ✅ |
| P2 | Add Card footer | `/admin/add-card` | Vault · Add Card · Analytics · Settings | ✅ |
| P2 | Analytics footer | `/admin/analytics` | Vault · Add Card · Analytics · Settings | ✅ |
| P2 | Settings footer | `/admin/settings` | Vault · Add Card · Analytics · Settings | ✅ |
| P3 | Active highlight | Each page | Current page button highlighted in blue | ✅ |
| P4 | No SOON badges | All footers | No "SOON" badge on any button | ✅ |

---

## 9. Mobile Responsiveness (390×844)

> **Precondition:** Chrome DevTools → toggle device toolbar → iPhone 14 (390×844).

| Pri | Test Case | Area | Expected Result | Pass/Fail |
|-----|-----------|------|-----------------|-----------| 
| P2 | No horizontal scroll | Marketplace | No unexpected horizontal scrollbar on any section | ✅ |
| P2 | Header layout | Marketplace | Logo + cart icon visible, no text overflow | ✅ |
| P2 | Search bar | Marketplace | Full width, no clipping, keyboard opens on tap | ✅ |
| P2 | Bottom nav | Marketplace | All 5 icons visible, tappable, no overlap | ✅ |
| P2 | Fresh Pulls grid | Marketplace | 2-column grid, card text readable | ✅ |
| P3 | Banner carousel | Marketplace | Full width, swipe works, dots centered | ✅ |
| P3 | What's Hot grid | Marketplace | 1-column layout, price/button not clipped | ✅ |
| P3 | All Cards grid | Marketplace | 2-column grid | ✅ |
| P3 | Footer | Marketplace | 2-column layout, no overflow | ✅ |
| P3 | Dashboard top | Admin | Header, search, status badges fit within viewport | ✅ |
| P3 | Leaderboard scroll | Admin | Horizontal swipe works without vertical jump | ✅ |
| P3 | Inventory chart | Admin | Chart.js renders, axis labels legible | ✅ |
| P3 | Card list | Admin | Card names fit, pagination works | ✅ |
| P3 | Add Card form | Admin | All inputs full-width, submit button visible | ✅ |
| P4 | Scroll-to-top | Marketplace | Button visible above bottom nav | ✅ |
| P4 | Login page | Auth | Form centered, usable on mobile | ✅ |
| P4 | Settings banners | Admin | Banner cards stack vertically, edit/delete accessible | ✅ |
| P4 | Analytics sections | Admin | PSA candidates, behavior cards stack | ✅ |
| P4 | Admin footer (all) | Admin | 4 buttons visible and tappable | ✅ |

---

## 10. Error Handling

> **Precondition:** Server running. Test both connected and disconnected states.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P2 | No auth access | Go to `/admin` without login | Redirects to `/admin/login` | ☐ |
| P3 | Invalid route | Go to `/this-does-not-exist` | 404 page or redirect to `/` | ☐ |
| P3 | API error | Disconnect network → click Sync | Graceful error message, no crash | ☐ |

---

## 11. Production-Specific Tests

> **Precondition:** App deployed to production at https://tcgnakama.com.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------| 
| P1 | Shopify token | Dashboard loads in production | Products display from live Shopify store | ✅ |
| P1 | HTTPS works | Visit https://tcgnakama.com | Secure connection (padlock icon) | ☐ |
| P2 | Env vars set | Check production app logs | No "missing env" errors at startup | ☐ |
| P3 | SESSION_SECRET | Login → wait 1 hour → refresh | Still logged in (session not expired) | ☐ |

---

## 12. Automated Test Suite

> [!TIP]
> Run via `/qa-test` workflow. Phases 1-2 are auto-run, Phase 3 is manual.

### 12a. Regression Test ([test_shopify_sync.py](file:///Users/saptayh/TCGNakama-1/tests/test_shopify_sync.py))

| Pri | Test Case | Type | What It Checks | Pass/Fail |
|-----|-----------|------|----------------|-----------|
| P1 | Single variant in stock | Unit | `_map_product` → totalInventory > 0, status=Sync | ✅ |
| P1 | Multi-variant (first OOS) | Unit | Any variant available → status=Sync | ✅ |
| P1 | Truly sold out | Unit | All variants OOS → status=Sold Out | ✅ |
| P2 | Prefers product totalInventory | Unit | Shopify's product-level value used over variant sum | ✅ |
| P1 | Collection products inventory | Live | `get_collection_products` returns stock > 0 for in-stock | ✅ |
| P1 | get_products has totalInventory | Live | `totalInventory` key present and ≥ 0 on all products | ✅ |

### 12b. Smoke Test ([smoke_test.py](file:///Users/saptayh/TCGNakama-1/scripts/smoke_test.py))

| Pri | Test Case | Endpoint | What It Checks | Pass/Fail |
|-----|-----------|----------|----------------|-----------|
| P1 | Homepage loads | GET / | HTTP 200, contains "What's Hot" + "Fresh Pulls" + cards | ✅ |
| P1 | Collection filter | GET /filter?collection=pokemon | HTTP 200, ≥1 product card with cart action | ✅ |
| P2 | Card detail page | GET /card/{id} | HTTP 200, contains "Add to Cart" | ✅ |
| P2 | Server health | GET / (repeated) | HTTP 200 on second request | ✅ |

### How To Run

```bash
# Regression tests (unit + live)
source .venv/bin/activate && python tests/test_shopify_sync.py

# Smoke tests (requires server on port 8001)
source .venv/bin/activate && python scripts/smoke_test.py

# Full QA workflow:
# /qa-test
```

---

## 14. Task Prioritization Sprint — Post-Implementation QA

> [!IMPORTANT]
> Run this entire section **after** all 7 tasks from the Feb 2026 Task Prioritization spreadsheet are implemented. Each sub-section maps to one task ID.

### 14a. ID 1 — AJAX Filter Persistence (CRITICAL — Tech Bug)

> **Precondition:** Server running, 50+ products synced, multiple pages available (20 per page).

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------|
| P1 | Rarity persists on Page 2 | Select "Rare" rarity → click "Next" | Page 2 shows only Rare cards, rarity pill stays highlighted | ☐ |
| P1 | Collection persists on Page 2 | Select "Pokemon" collection → click "Next" | Page 2 shows only Pokémon, collection badge stays active | ☐ |
| P1 | Price filter persists | Set max price ¥5,000 → click "Next" | Page 2 shows only cards ≤ ¥5,000 | ☐ |
| P1 | Combined filters + pagination | Set Rare + Pokemon + max ¥10,000 → click "Next" | All 3 filters stay active on page 2 | ☐ |
| P2 | "Previous" preserves filters | Page 2 with filters → click "Previous" | Page 1 with same filters active | ☐ |
| P2 | Vault count shows total | Apply filter with 35 results → view page 1 (20 items) | Counter reads "35 in vault", not "20" | ☐ |
| P2 | Search + filter + pagination | Type "Charizard" + select Rare → click "Next" | Search query + rarity both preserved | ☐ |
| P2 | Mobile sheet → Next page | Mobile: open filter sheet → pick Rare → "Show Results" → "Next" | Filter persists on mobile layout | ☐ |
| P3 | Page 1 no regression | Load homepage with no filters → click "Next" → "Previous" | All products display correctly, no stale parameters | ☐ |

### 14b. ID 2 — Card Metadata (Set Name, Card #, Condition)

> **Precondition:** At least 5 products with `set:`, `number:`, `condition:` Shopify tags.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------|
| P1 | Grid shows card number | View product grid card | Card number (e.g., "OP10-001") visible below set name | ☐ |
| P1 | Grid shows condition | View card with `condition:Raw` tag | "Raw" visible next to card number | ☐ |
| P2 | Missing metadata hidden | View card without `number:` tag | No "#000" placeholder shown — line is hidden | ☐ |
| P1 | PDP description renders | Click into card detail page | "Description" section shows Shopify HTML content | ☐ |
| P2 | PDP metadata pills complete | View PDP of fully-tagged card | Rarity pill + Condition pill + Edition pill visible | ☐ |
| P2 | Card Details table complete | View PDP Card Details section | Set Code, Set, Collection, Seller, Stock, Condition all populated | ☐ |
| P3 | Description sanitized | View PDP with HTML in description | HTML renders correctly (bold, lists), no XSS vectors | ☐ |

### 14c. ID 3 — TCG Condition Guide Modal

> **Precondition:** At least 1 product with a condition tag (e.g., `condition:NM`).

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------|
| P2 | Condition pill opens modal | PDP → click condition pill (e.g., "NM") | Condition guide modal appears with NM/LP/MP/HP/DMG table | ☐ |
| P2 | Modal content accurate | Read modal body | All 5 grades listed with abbreviation + description | ☐ |
| P2 | Close via ✕ button | Click ✕ in top-right of modal | Modal closes, page scrollable again | ☐ |
| P2 | Close via backdrop | Click dark backdrop area outside modal | Modal closes | ☐ |
| P3 | "What's this?" link | PDP → Card Details → Condition row → click link | Same modal opens | ☐ |
| P3 | Info icon visible | View condition pill on PDP | Small ℹ️ icon visible next to condition text | ☐ |
| P3 | Modal styling matches design system | Visual inspection | Dark glassmorphism, primary accent borders, correct typography | ☐ |
| P4 | No scroll lock leak | Open modal → close → scroll page | Page scrolls normally, no stuck `overflow:hidden` | ☐ |

### 14d. ID 4 — Trust Badge Integration (CRO)

> **Precondition:** Any product detail page loaded.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------|
| P2 | PDP trust strip visible | View any PDP below "Add to Cart" | 3 badges: "Authenticity Guaranteed", "Secure Shipping", "Ships Next Day" | ☐ |
| P2 | Badge icons render | View trust strip | ✓ verified (green), 🛡 shield (blue), 📦 shipping (gold) icons display | ☐ |
| P3 | Grid card trust indicator | View product card in All Cards grid | Compact "Authentic · Secure Ship" text with ✓ icon below price | ☐ |
| P3 | Mobile PDP badges | View PDP at 390px width | Trust badges wrap gracefully, all 3 readable | ☐ |
| P4 | Sold-out card no badges | View a sold-out product PDP | Trust strip still visible (builds confidence for wishlist/restock) | ☐ |

### 14e. ID 5 — SEO H1/Metadata Audit

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------|
| P2 | Homepage `<title>` | View page source at `/` | `<title>` contains "TCG Nakama" + descriptive text, not generic | ☐ |
| P2 | Homepage single `<h1>` | View page source at `/` | Exactly 1 `<h1>` element (logo text) | ☐ |
| P2 | Homepage meta description | View page source at `/` | `<meta name="description">` present with 120-160 char content | ☐ |
| P2 | PDP `<title>` unique | View page source at `/card/{id}` | `<title>` contains product name + set name | ☐ |
| P2 | PDP single `<h1>` | View page source at PDP | Exactly 1 `<h1>` = product title (logo demoted to `<span>`) | ☐ |
| P2 | PDP meta description dynamic | View page source at PDP | `<meta name="description">` includes product title, rarity, price | ☐ |
| P3 | Canonical URL present | View page source on PDP | `<link rel="canonical">` with clean URL | ☐ |
| P3 | Meta keywords set | View page source | `<meta name="keywords">` contains relevant card terms | ☐ |

### 14f. ID 6 — Mobile Image Optimization (Performance)

> **Precondition:** Chrome DevTools open, Network tab active, filter by "Img".

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------|
| P2 | Hero uses `<picture>` + WebP | View page source → hero banner | `<picture>` with `<source type="image/webp">` and `srcset` widths | ☐ |
| P2 | Grid images request WebP | Network tab → filter images from grid | Image URLs contain `&format=webp` parameter | ☐ |
| P2 | PDP images request WebP | Load a card detail page → Network tab | PDP carousel image URLs contain `&format=webp` | ☐ |
| P2 | Lazy loading on grid | View page source → All Cards grid | `loading="lazy"` on all grid `<img>` tags | ☐ |
| P3 | Hero image eager load | View page source → hero banner | First banner `<img>` has `loading="eager"` + `fetchpriority="high"` | ☐ |
| P3 | PageSpeed Mobile ≥ 75 | Run Google PageSpeed Insights on homepage URL | Mobile score ≥ 75 | ☐ |
| P4 | Responsive srcset widths | Resize to mobile (390px) → Network tab | Hero loads ~480w image, not full 1920w | ☐ |

### 14g. ID 7 — Ghost Inventory Logic Fix

> **Precondition:** At least 1 sold-out product exists in Shopify.

| Pri | Test Case | Steps | Expected Result | Pass/Fail |
|-----|-----------|-------|-----------------|-----------|
| P1 | Vault count matches grid | Load All Cards grid page 1 | "X in vault" counter equals total filtered products (not just page slice) | ☐ |
| P1 | No ghost sold-out in grid | Load All Cards → scan full grid | No cards with "Sold Out" overlay visible in default view | ☐ |
| P2 | Sold-out hidden from filter | Select a collection filter | Sold-out products do not appear in results | ☐ |
| P2 | Sold-out hidden from search | Search for a sold-out product by name | Product does not appear in grid results | ☐ |
| P1 | Sold-out PDP still accessible | Direct-navigate to `/card/{sold-out-id}` | PDP loads with "SOLD OUT" button, card details visible | ☐ |
| P2 | Count updates after Resync | Click Resync → check count | Count reflects fresh Shopify inventory | ☐ |
| P3 | Pagination count consistent | Filter shows 45 results → check | Page 1: "45 in vault", Page 2: "45 in vault", Page 3: "45 in vault" | ☐ |

## 13. Defect Log

> Track all discovered bugs, their severity, and resolution. Add new entries as defects are found during QA runs.

| ID | Date | Section | Description | Pri | Status | Resolution |
|----|------|---------|-------------|-----|--------|------------|
| D001 | 2026-02-19 | 1b | Ghost Sold-Out: all collection-filtered cards showed "Sold Out" because `get_collection_products()` query was missing `quantityAvailable` and used `variants(first:1)` | P1 | ✅ Fixed | Added `quantityAvailable` + `totalInventory`, expanded to `variants(first:10)` |
| D002 | 2026-02-19 | 1b | `_map_product` only checked first variant's `availableForSale` — multi-variant products with first variant OOS showed Sold Out | P1 | ✅ Fixed | Changed to `any()` check across all variants |
| D003 | 2026-02-19 | 12b | Smoke test: `get_products()` query missing product-level `totalInventory` field | P2 | ✅ Fixed | Added `totalInventory` to `get_products` GraphQL query |
| D004 | 2026-02-24 | 14a | AJAX filter params lost on pagination: Next/Previous buttons in `product_grid.html` hard-code `/filter?page=N` without `hx-include` | P1 | ⏳ Open | Pending — add `hx-include="#filter-form, #search-input"` to pagination buttons |
| D005 | 2026-02-24 | 14g | Ghost inventory: sidebar "X in vault" uses `products|length` (page slice) not `total_products`; sold-out products inflate grid count | P1 | ⏳ Open | Pending — use `total_products` + filter `totalInventory == 0` before paginating |
| D006 | 2026-02-24 | 14e | SEO: `card_details.html` has 2 `<h1>` tags (logo + product title); `base.html` has hard-coded generic `<title>` with no meta description | P2 | ⏳ Open | Pending — demote logo to `<span>`, add dynamic `<title>` / `<meta>` blocks |
| D007 | 2026-02-24 | 14f | All images served as original format (JPEG/PNG), no WebP requested from Shopify CDN; hero banners lack `<picture>` / `srcset` | P2 | ⏳ Open | Pending — append `&format=webp` to image URLs, add `<picture>` for hero |

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| QA Tester | | | |
| Product Owner | | | |

> [!NOTE]
> **Sprint Scope:** Section 14 was added on 2026-02-24 to cover the 7-task prioritization sprint. All ☐ items in Section 14 must reach ✅ before the sprint is considered "Done."
