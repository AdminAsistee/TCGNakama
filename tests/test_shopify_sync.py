"""
TCG Nakama — Ghost Sold-Out Regression Test
=============================================
Validates that _map_product() correctly determines stock status
and that collection queries return proper inventory data.

Usage:
    source .venv/bin/activate && python tests/test_shopify_sync.py

Tests 1-3: Pure unit tests (no API call, no .env needed)
Tests 4-5: Live integration tests (requires .env with Shopify credentials)
"""

import asyncio
import sys
import os

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.dependencies import ShopifyClient

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


def make_node(variants_data: list, total_inventory=None) -> dict:
    """Build a minimal Shopify product node for _map_product testing."""
    node = {
        "id": "gid://shopify/Product/99999",
        "title": "Test Card",
        "tags": ["set:Base Set", "rarity:Rare"],
        "handle": "test-card",
        "createdAt": "2025-01-01T00:00:00Z",
        "featuredImage": {"url": "https://example.com/img.jpg"},
        "images": {"edges": [{"node": {"url": "https://example.com/img.jpg"}}]},
        "variants": {
            "edges": [
                {
                    "node": {
                        "id": f"gid://shopify/ProductVariant/{i}",
                        "availableForSale": v["available"],
                        "quantityAvailable": v["qty"],
                        "price": {"amount": "100.0", "currencyCode": "JPY"},
                    }
                }
                for i, v in enumerate(variants_data)
            ]
        },
    }
    if total_inventory is not None:
        node["totalInventory"] = total_inventory
    return node


# ─────────────────────────────────────────────
# UNIT TESTS (no API call)
# ─────────────────────────────────────────────

def test_map_product_in_stock():
    """If quantityAvailable > 0, product must be In Stock (status=Sync)."""
    print("\n[Test 1] _map_product — single variant in stock")
    client = ShopifyClient()
    node = make_node([{"available": True, "qty": 5}])
    result = client._map_product(node)
    report("totalInventory > 0", result["totalInventory"] > 0,
           f"got {result['totalInventory']}")
    report("status == 'Sync'", result["status"] == "Sync",
           f"got '{result['status']}'")


def test_map_product_multi_variant():
    """If variant 1 is OOS but variant 2 is available → status must be Sync."""
    print("\n[Test 2] _map_product — multi-variant (first OOS, second available)")
    client = ShopifyClient()
    node = make_node([
        {"available": False, "qty": 0},  # variant 1: sold out
        {"available": True, "qty": 3},   # variant 2: in stock
    ])
    result = client._map_product(node)
    report("totalInventory == 3", result["totalInventory"] == 3,
           f"got {result['totalInventory']}")
    report("status == 'Sync' (any variant available)", result["status"] == "Sync",
           f"got '{result['status']}'")


def test_map_product_sold_out():
    """All variants OOS → status must be Sold Out."""
    print("\n[Test 3] _map_product — truly sold out")
    client = ShopifyClient()
    node = make_node([
        {"available": False, "qty": 0},
        {"available": False, "qty": 0},
    ])
    result = client._map_product(node)
    report("totalInventory == 0", result["totalInventory"] == 0,
           f"got {result['totalInventory']}")
    report("status == 'Sold Out'", result["status"] == "Sold Out",
           f"got '{result['status']}'")


def test_map_product_prefers_totalInventory():
    """When Shopify provides product-level totalInventory, prefer it."""
    print("\n[Test 3b] _map_product — prefers product-level totalInventory")
    client = ShopifyClient()
    # Variant says qty=2 but product-level totalInventory says 10
    node = make_node([{"available": True, "qty": 2}], total_inventory=10)
    result = client._map_product(node)
    report("totalInventory uses product-level value (10)", result["totalInventory"] == 10,
           f"got {result['totalInventory']}")


# ─────────────────────────────────────────────
# LIVE INTEGRATION TESTS (requires .env)
# ─────────────────────────────────────────────

async def test_collection_products_inventory():
    """get_collection_products must return totalInventory > 0 for in-stock items."""
    print("\n[Test 4] get_collection_products('pokemon') — live inventory check")
    client = ShopifyClient()
    try:
        products = await client.get_collection_products(handle="pokemon", first=10)
        report("returns products", len(products) > 0,
               f"got {len(products)} products")

        if products:
            in_stock = [p for p in products if p["totalInventory"] > 0]
            report("in-stock products have totalInventory > 0", len(in_stock) > 0,
                   f"{len(in_stock)}/{len(products)} have stock")

            for p in in_stock[:3]:  # Check up to 3
                report(f"  '{p['title']}' status=Sync",
                       p["status"] == "Sync",
                       f"totalInventory={p['totalInventory']}, status={p['status']}")
    except Exception as e:
        report("API call succeeded", False, str(e))
    finally:
        s_client = client.get_client()
        await s_client.aclose()


async def test_get_products_has_totalInventory():
    """get_products must include totalInventory for all products."""
    print("\n[Test 5] get_products() — totalInventory field present")
    client = ShopifyClient()
    try:
        products = await client.get_products()
        report("returns products", len(products) > 0,
               f"got {len(products)} products")

        if products:
            all_have_key = all("totalInventory" in p for p in products)
            report("all products have 'totalInventory' key", all_have_key)

            in_stock = [p for p in products if p["totalInventory"] > 0]
            report(f"{len(in_stock)}/{len(products)} products have stock > 0",
                   len(in_stock) > 0)
    except Exception as e:
        report("API call succeeded", False, str(e))
    finally:
        s_client = client.get_client()
        await s_client.aclose()


# ─────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────

async def main():
    print("=" * 55)
    print("  TCG Nakama — Shopify Sync Regression Test Suite")
    print("=" * 55)

    # Unit tests (no API)
    test_map_product_in_stock()
    test_map_product_multi_variant()
    test_map_product_sold_out()
    test_map_product_prefers_totalInventory()

    # Live integration tests
    token = os.getenv("SHOPIFY_STOREFRONT_TOKEN")
    if token:
        print("\n" + "-" * 55)
        print("  Live Integration Tests (Shopify API)")
        print("-" * 55)
        await test_collection_products_inventory()
        await test_get_products_has_totalInventory()
    else:
        print("\n⚠️  Skipping live tests — SHOPIFY_STOREFRONT_TOKEN not set")

    # Summary
    print("\n" + "=" * 55)
    total = passed + failed
    if failed == 0:
        print(f"  ✅ ALL {total} TESTS PASSED")
    else:
        print(f"  ❌ {failed}/{total} TESTS FAILED:")
        for e in errors:
            print(f"     • {e}")
    print("=" * 55)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
