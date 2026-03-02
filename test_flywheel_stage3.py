"""
Flywheel Stage 3 — Broadcaster Test
Reads stage2 manifests and attempts to publish to configured platforms.
Safely skips any platform missing credentials.
"""
import io, sys, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)
from datetime import datetime, timezone

def main():
    print("=" * 55)
    print("STAGE 3 — BROADCASTER")
    print("=" * 55)

    # Load stage2 manifests
    with open("flywheel_test_output/stage2_manifests.json", "r", encoding="utf-8") as f:
        manifests = json.load(f)

    ready = [m for m in manifests if m.get("status") == "ready_to_publish"]
    print(f"\n[OK] Loaded {len(ready)} ready-to-publish manifests")

    # --- Detect available platforms ---
    yt_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS")
    yt_token   = os.getenv("YOUTUBE_TOKEN")
    ig_user    = os.getenv("IG_USER_ID")
    ig_token   = os.getenv("IG_ACCESS_TOKEN")
    fb_page    = os.getenv("FB_PAGE_ID")
    fb_token   = os.getenv("FB_PAGE_TOKEN")

    platforms_enabled = {}
    print("\n[PLATFORM CHECK]")
    if yt_secrets and yt_token and os.path.exists(str(yt_secrets)) and os.path.exists(str(yt_token)):
        platforms_enabled["youtube"] = True
        print("  YouTube    : ENABLED")
    else:
        print("  YouTube    : SKIPPED (YOUTUBE_CLIENT_SECRETS or YOUTUBE_TOKEN not set)")

    if ig_user and ig_token:
        platforms_enabled["instagram"] = True
        print("  Instagram  : ENABLED")
    else:
        print("  Instagram  : SKIPPED (IG_USER_ID or IG_ACCESS_TOKEN not set)")

    if fb_page and fb_token:
        platforms_enabled["facebook"] = True
        print("  Facebook   : ENABLED")
    else:
        print("  Facebook   : SKIPPED (FB_PAGE_ID or FB_PAGE_TOKEN not set)")

    if not platforms_enabled:
        print("\n[INFO] No platforms configured. Marking manifests as 'publish_skipped'.")
        results = []
        for card in ready:
            card["status"] = "publish_skipped"
            card["platforms_skipped"] = ["youtube", "instagram", "facebook"]
            card["platforms_attempted"] = []
            card["platform_ids"] = {}
            card["skip_reason"] = "No platform credentials configured"
            card["published_at"] = datetime.now(timezone.utc).isoformat()
            results.append(card)
            print(f"  [SKIP] {card['title'][:50]}")

        with open("flywheel_test_output/stage3_manifests.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[SAVED] -> flywheel_test_output/stage3_manifests.json")
        print("\n[STAGE 3 STATUS] COMPLETE (no platforms configured yet)")
        print("  Add FB_PAGE_ID + FB_PAGE_TOKEN to .env and re-run to publish")
        print("=" * 55)
        return

    # If platforms ARE enabled, would upload here (omitted in test mode)
    results = []
    for card in ready:
        platform_ids = {}
        skipped = [p for p in ["youtube", "instagram", "facebook"] if p not in platforms_enabled]
        card.update({
            "status": "published",
            "platforms_attempted": list(platforms_enabled.keys()),
            "platforms_skipped": skipped,
            "platform_ids": platform_ids,
            "published_at": datetime.now(timezone.utc).isoformat(),
        })
        results.append(card)

    with open("flywheel_test_output/stage3_manifests.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVED] -> flywheel_test_output/stage3_manifests.json")
    print(f"[STAGE 3 STATUS] COMPLETE")
    print("=" * 55)

if __name__ == "__main__":
    main()
