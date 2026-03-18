---
description: Pre-flight design check before modifying any HTML template
---

# Design Check Workflow

Run this checklist before modifying any `.html` template file.

1. Read `.agent/context/design-system.md` to understand the current design system.
2. Determine which design mode this page uses:
   - Storefront pages → **Vault mode** (dark `#0B1120`, gold accents)
   - Admin pages (`/admin/*`, `/seller-admin/*`) → **Utility mode** (light `#f3f4f6`)
   - Seller portal (`/seller/*`) → **Vault mode**
3. Use the correct color tokens from `tailwind.config.js`. **Never use raw hex values.**
4. Follow component patterns from the design system. **Do not invent new button styles.**
5. Use existing effect classes (`obsidian-glass`, `gold-glow`, etc.) instead of custom CSS.
6. Test responsive behavior at mobile (375px) and desktop (1280px).
7. If adding new icons, add them to the `icon_names=` list in `base.html` Material Symbols link.
