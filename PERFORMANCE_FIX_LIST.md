# Performance Fix List — TCGNakama
Generated: 2026-03-02
PSI Scores Before: Mobile **57** / Desktop **89**

## ✅ All Changes Complete

### Mobile Impact Fixes
- [x] **HTMX defer** → `base.html` (line 16) — removes 16.5KB render-blocking script → Target: FCP, LCP
- [x] **Google Fonts preconnect** → `base.html` — reduces DNS/TCP time for fonts.googleapis.com + fonts.gstatic.com → Target: FCP
- [x] **font-display: swap** → Google Fonts URL now has `&display=swap` → Target: CLS, FCP
- [x] **Logo WebP conversion** → `live_logo.png` (260KB) → `live_logo.webp` (25KB, 90% smaller) → Target: LCP, Mobile payload
- [x] **Logo img dimensions** → `index.html`, `card_details.html` now have `width="32" height="32"` → Target: CLS

### Desktop Impact Fixes
- [x] **Tailwind CDN → compiled CSS** → `base.html` CDN script (127KB, render-blocking) replaced with `<link rel="stylesheet" href="/static/tailwind.css">` (55KB, non-blocking) → Target: FCP, LCP, TBT
- [x] **preconnect to cdn.jsdelivr.net** → `base.html` → Target: FCP (HTMX load faster)

### Universal Fixes
- [x] Tailwind tree-shaken: 127KB CDN → 55KB compiled (57% smaller)
- [x] Logo PNG → WebP: 260KB → 25KB (90% smaller)
- [x] All banners already WebP ✅ (no changes needed)
- [x] `font-display: swap` prevents invisible text flash (FOIT)

## Files Changed
| File | Change |
|------|--------|
| `app/templates/base.html` | Removed Tailwind CDN + 100-line inline style block; added compiled CSS link, preconnect hints, font-display:swap, HTMX defer |
| `app/templates/index.html` | Logo → WebP, added width/height |
| `app/templates/card_details.html` | Logo → WebP, added width/height |
| `app/static/live_logo.webp` | NEW — 25KB WebP version of logo |
| `app/static/tailwind.css` | NEW — compiled, minified Tailwind (55KB, tree-shaken) |
| `tailwind.config.js` | NEW — Tailwind v3 config for future rebuilds |
| `tailwind.input.css` | NEW — input CSS with all custom classes |

## Next Steps (After Deploy)
1. Run `git add -A && git commit -m "perf: compile Tailwind, WebP logo, defer HTMX, add preconnect" && git push heroku main`
2. Re-run PSI at https://pagespeed.web.dev/
3. Paste new Mobile + Desktop scores to verify improvements
