# Legacy Test Archive

This directory contains **70 ad-hoc debug scripts** from development. They are **not part of the test suite** and are kept for reference only.

## Why they're here

These scripts were created during development to debug specific features. They:
- Hit `localhost:8001` directly (require a running server)
- Need live API keys (Gemini, Shopify, PriceCharting)
- Use `asyncio.run(main())` instead of `pytest` conventions
- Have significant duplication (e.g. 5 appraisal variants, 9 bulk upload variants)

## How to run proper tests

```bash
python -m pytest tests/ -v --ignore=tests/archive
```

## Can I delete these?

Yes — they contain no logic that isn't covered by the proper test suite. Keep them only if you need to reference how a specific feature was manually tested during development.
