---
description: QA testing workflow — token-efficient strategy for verifying routes, auth, and UI
---

# QA Testing Workflow

// turbo-all

## Priority Order (cheapest → most expensive)

### 1. Python/curl Script Testing (preferred for logic)
Use for: route auth, redirects, session cookies, DB state, API responses.

```bash
# Example: verify a route accepts seller session
python -c "
import httpx
r = httpx.get('http://localhost:8001/admin/add-card',
    cookies={'seller_session': '<token>'},
    follow_redirects=False)
print(f'Status: {r.status_code}')  # 200 = PASS, 302 = FAIL
"
```

**When to use:**
- Checking if a route returns 200 vs 302 redirect
- Verifying session/cookie behavior
- Testing email delivery (call the function directly)
- Checking DB state (query with SQLAlchemy)
- Verifying API JSON responses

### 2. Browser Subagent — Visual Checks Only (expensive)
Use for: layout verification, placeholder text, color/styling, responsive design.

**Rules:**
- Max **5 interaction steps** per subagent call
- Never ask "explore and report what you see" — specify exactly what to verify
- Never dump the full DOM — use screenshots for visual checks
- One focused test per subagent call (e.g., "login and verify dashboard layout")
- Do NOT use browser subagent to test auth/redirects — use Python scripts instead

**Good task:**
> Navigate to /seller/login, take a screenshot, verify fields are empty and dark-themed

**Bad task:**
> Test the entire seller flow: register, login, check all buttons, logout, test footer

### 3. Batch Related Checks
Group related non-visual tests into a single Python script:

```python
# Test all seller routes in one script
routes = ["/admin/add-card", "/admin/bulk-upload", "/admin"]
for route in routes:
    r = httpx.get(f"http://localhost:8001{route}",
        cookies={"seller_session": token},
        follow_redirects=False)
    status = "PASS" if r.status_code == 200 else "FAIL"
    print(f"{route}: {status} ({r.status_code})")
```

## Decision Matrix

| What to test | Method | Est. tokens |
|---|---|---|
| Route returns correct status code | Python script | ~500 |
| Session/cookie auth works | Python script | ~500 |
| Email sends successfully | Python function call | ~500 |
| DB record created/deleted | Python + SQLAlchemy | ~500 |
| Page layout looks correct | Browser (screenshot only) | ~15,000 |
| Full user flow (login→action→logout) | Browser (multi-step) | ~40,000 |
| "Test everything" | ❌ Never do this | ~80,000+ |
