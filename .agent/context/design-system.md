---
name: Design System Reference
description: TCGNakama UI/UX design tokens, component patterns, and rules for maintaining visual consistency across the storefront, admin, and seller portal.
---

# TCGNakama Design System

> Read this before modifying any `.html` template or CSS file.

## Design Modes

| Mode | Pages | Background | Text |
|---|---|---|---|
| **Vault (Storefront)** | Homepage, card detail, blog, cart, about | `#0B1120` | White/gray |
| **Admin (Dashboard)** | `/admin/*`, `/seller-admin/*` | `#f3f4f6` | Dark gray/black |
| **Seller Portal** | `/seller/*` | `#0B1120` | White |

## Color Tokens (from `tailwind.config.js`)

| Token | Hex | Usage |
|---|---|---|
| `primary` | `#FFD700` | Brand gold — CTAs, active nav, prices, badges |
| `primary-dark` | `#B8960F` | Button hover |
| `background-dark` | `#0B1120` | Page background (storefront) |
| `surface` | `#111827` | Card backgrounds, panels |
| `surface-light` | `#1F2937` | Elevated surfaces, borders |
| `neon-red` | `#EF4444` | Sold out, errors, cart badge |
| `neon-green` | `#22C55E` | In stock, success, price gainers |
| `accent-blue` | `#3B82F6` | Links, info badges |

## Typography

- **Font**: Space Grotesk (400, 600) via Google Fonts
- **Icons**: Material Symbols Outlined (38 selectively loaded)
- **Labels**: `text-[10px] font-bold uppercase tracking-wider text-gray-400`
- **Prices**: `text-sm font-black text-primary`

## Custom Effect Classes

| Class | Use For |
|---|---|
| `obsidian-glass` | Modal overlays, elevated panels |
| `glass-hero` | Hero sections |
| `holographic-glow` | Premium card highlights |
| `gold-glow` | CTA buttons |
| `vault-card-outline` | Product card borders |
| `live-pulse` | "LIVE" badges |

## Component Patterns

| Component | Tailwind Classes |
|---|---|
| **Product card** | `bg-surface rounded-xl border border-white/[0.1]` |
| **CTA button** | `bg-primary text-background-dark font-black rounded-full` |
| **Ghost button** | `bg-primary/15 border border-primary/30 text-primary` |
| **Filter pill** | `rounded-full border border-white/10 bg-white/5 text-gray-300` |
| **Dropdown** | `bg-surface border border-white/10 rounded-xl shadow-2xl` |

## Interaction Stack

- **Search/filter**: HTMX `hx-get="/filter"` with 300ms debounce
- **Cart**: Fetch API → optimistic UI → revert on error
- **Carousel**: Pure JS + CSS `transition-transform`
- **Loading**: `htmx-indicator` class + spinning Material Symbol `sync`

## Do's and Don'ts

### ✅ Do
- Use Tailwind token names (`bg-primary`, `text-neon-green`), never raw hex
- Use existing effect classes (`obsidian-glass`, `gold-glow`)
- Follow the border pattern: `border border-white/[0.1]` or `border-white/10`
- Test at mobile (375px) and desktop (1280px)

### ❌ Don't
- Invent new button styles — use CTA or Ghost patterns
- Use plain colors (`bg-red-500`) — use semantic tokens (`bg-neon-red`)
- Add new fonts without updating `base.html` preload hints
- Use inline styles when a Tailwind utility exists
