"""
Flywheel Stage 1 — Producer Test
Fetches Fresh Pulls from Shopify and identifies cards qualifying for video production.
"""
import io, sys, asyncio, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)

PRICE_THRESHOLD = 7500  # JPY

async def main():
    from app.dependencies import ShopifyClient
    from app.routers.store import _calc_listed_ago

    print("=" * 55)
    print("STAGE 1 — PRODUCER")
    print("=" * 55)

    client = ShopifyClient()
    products = await client.get_products()
    print(f"\n[OK] Fetched {len(products)} products from Shopify")

    # Add listed_ago label
    for p in products:
        p['listed_ago'] = _calc_listed_ago(p)

    # Fresh Pulls: newest 8 in stock
    in_stock = [p for p in products if p.get('totalInventory', 0) > 0]
    fresh_pulls = sorted(in_stock, key=lambda x: x.get('createdAt', ''), reverse=True)[:8]

    print(f"\n[FRESH PULLS] Top {len(fresh_pulls)} newest in-stock cards:")
    print(f"  {'Title':<42} {'Price':>8}  {'Stock':>6}  {'Age'}")
    print(f"  {'-'*42} {'-'*8}  {'-'*6}  {'-'*11}")
    for p in fresh_pulls:
        title = p['title'][:42]
        print(f"  {title:<42} {p['price']:>8.0f}  {p.get('totalInventory',0):>6}  {p['listed_ago']}")

    # Producer filter: price >= threshold
    qualifying = [p for p in fresh_pulls if p.get('price', 0) >= PRICE_THRESHOLD]
    print(f"\n[PRODUCER FILTER] Cards >= JPY {PRICE_THRESHOLD:,} in Fresh Pulls: {len(qualifying)}")

    if not qualifying:
        print(f"\n[INFO] No Fresh Pull cards meet the price threshold.")
        print(f"[INFO] Lowest price in Fresh Pulls: JPY {min(p['price'] for p in fresh_pulls):,.0f}" if fresh_pulls else "")
        print(f"[INFO] To test the full pipeline, threshold can be lowered.")
        # Use all fresh pulls as test candidates regardless
        qualifying = fresh_pulls[:2]
        print(f"[INFO] Using top {len(qualifying)} Fresh Pulls for pipeline test regardless of price.")

    print(f"\n[MANIFESTS] Would produce video + manifest for:")
    manifests = []
    for p in qualifying:
        safe_id = p['id'].split('/')[-1]
        manifest = {
            "card_id": p['id'],
            "safe_id": safe_id,
            "title": p['title'],
            "price_jpy": p['price'],
            "rarity": p.get('rarity', 'Unknown'),
            "set": p.get('set', 'Unknown'),
            "card_number": p.get('card_number', ''),
            "image_url": p.get('image', ''),
            "listed_ago": p['listed_ago'],
            "status": "pending_qa",
            "gcs_video_uri": f"gs://ready-bucket/queue/{safe_id}/final.mp4",
            "gcs_manifest_uri": f"gs://ready-bucket/queue/{safe_id}/manifest.json",
        }
        manifests.append(manifest)
        print(f"  - {p['title'][:45]}")
        print(f"    Price: JPY {p['price']:,.0f} | Rarity: {p.get('rarity')} | Listed: {p['listed_ago']}")
        print(f"    Manifest: gs://ready-bucket/queue/{safe_id}/manifest.json")

    # Save test manifests locally
    os.makedirs("flywheel_test_output", exist_ok=True)
    with open("flywheel_test_output/stage1_manifests.json", "w", encoding="utf-8") as f:
        json.dump(manifests, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVED] Test manifests -> flywheel_test_output/stage1_manifests.json")

    print("\n[STAGE 1 STATUS] COMPLETE")
    print("  Next: Copywriter would QA video frames + write captions")
    print("  (Veo video generation skipped in test mode — no video rendered)")
    print("=" * 55)

    return manifests

if __name__ == "__main__":
    asyncio.run(main())
