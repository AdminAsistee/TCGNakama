"""
TCG Nakama — Smoke Test
========================
Lightweight HTTP smoke test that validates the running app
serves correct pages with expected content.

Usage:
    # Ensure server is running on port 8001 first
    source .venv/bin/activate && python scripts/smoke_test.py

    # Custom base URL:
    BASE_URL=http://localhost:3000 python scripts/smoke_test.py
"""

import os
import sys
import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")
TIMEOUT = 30.0  # seconds — card detail pages can be slow due to Shopify API calls

# ─────────────────────────────────────────────
# Test utilities
# ─────────────────────────────────────────────
passed = 0
failed = 0
errors = []

def report(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        errors.append(name)
        print(f"  ❌ {name}{' — ' + detail if detail else ''}")


def check_response(name: str, response: httpx.Response, 
                   required_strings: list[str] = None,
                   forbidden_strings: list[str] = None):
    """Check HTTP status and content of a response."""
    report(f"{name} → HTTP {response.status_code}", response.status_code == 200,
           f"got {response.status_code}")
    
    if response.status_code != 200:
        return
    
    body = response.text
    
    if required_strings:
        for s in required_strings:
            report(f"  contains '{s}'", s.lower() in body.lower(),
                   f"not found in response body ({len(body)} chars)")
    
    if forbidden_strings:
        for s in forbidden_strings:
            report(f"  does NOT contain '{s}'", s.lower() not in body.lower(),
                   "found in response body (unexpected)")


# ─────────────────────────────────────────────
# Smoke tests
# ─────────────────────────────────────────────

def run_tests():
    print("=" * 55)
    print("  TCG Nakama — Smoke Test Suite")
    print(f"  Target: {BASE_URL}")
    print("=" * 55)

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        
        # ── Test 1: Homepage ──
        print("\n[Test 1] Homepage (GET /)")
        try:
            r = client.get(f"{BASE_URL}/")
            check_response("Homepage loads", r,
                required_strings=["TCGNakama", "What's Hot", "Fresh Pulls"],
            )
            
            # Check product grid has actual cards (not empty)
            has_cards = "Add" in r.text or "ADD" in r.text or "add-to-cart" in r.text.lower()
            report("  product grid has cards", has_cards,
                   "no Add/ADD buttons found — grid may be empty")
        except httpx.ConnectError:
            report("Homepage loads", False, 
                   f"Cannot connect to {BASE_URL} — is the server running?")
            print(f"\n  💡 Start the server first:")
            print(f"     source .venv/bin/activate && uvicorn app.main:app --reload --port 8001\n")
            return  # No point continuing if server is down

        # ── Test 2: Collection filter ──
        print("\n[Test 2] Collection filter (GET /filter?collection=pokemon)")
        r = client.get(f"{BASE_URL}/filter", params={"collection": "pokemon"})
        check_response("Pokemon filter loads", r,
            required_strings=["ADD"],
        )
        # Check we got multiple cards
        card_count = r.text.lower().count('add to cart') + r.text.lower().count('handlecartaction')
        report(f"  has product cards ({card_count} cart action references found)", card_count > 0)

        # ── Test 3: Sample product page ──
        print("\n[Test 3] Product detail page")
        # First, extract a product ID from the homepage
        import re
        homepage = client.get(f"{BASE_URL}/").text
        # Card links use gid://shopify/Product/XXXXX format
        product_ids = re.findall(r'/card/(gid://shopify/Product/\d+)', homepage)
        
        if product_ids:
            sample_id = product_ids[0]
            from urllib.parse import quote
            encoded_id = quote(sample_id, safe='')
            try:
                r = client.get(f"{BASE_URL}/card/{encoded_id}")
                check_response(f"Card detail page loads", r,
                    required_strings=["Add to Cart"],
                )
            except httpx.ReadTimeout:
                report(f"Card detail page loads", False,
                       f"timed out after {TIMEOUT}s — Shopify API may be slow")
        else:
            report("Card detail page loads", False, 
                   "could not find any product ID link on homepage")

        # ── Test 4: Server health ──
        print("\n[Test 4] Server health")
        r = client.get(f"{BASE_URL}/")
        report("Server responds to repeated requests", r.status_code == 200)


    # ── Summary ──
    print("\n" + "=" * 55)
    total = passed + failed
    if failed == 0:
        print(f"  ✅ ALL {total} CHECKS PASSED")
    else:
        print(f"  ❌ {failed}/{total} CHECKS FAILED:")
        for e in errors:
            print(f"     • {e}")
    print("=" * 55)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run_tests()
