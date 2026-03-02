"""
Flywheel Stage 2 — Copywriter Test
Reads stage1 manifests and generates platform captions using Gemini.
(QA frame extraction skipped in test mode — no video exists yet.)
"""
import io, sys, asyncio, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)

async def generate_captions(card: dict) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""You are a TCG trading card content creator writing short-form social media captions.

Card details:
- Name: {card['title']}
- Set: {card['set']} | Card Number: {card['card_number']}
- Rarity: {card['rarity']}
- Price: JPY {card['price_jpy']}
- Freshness: {card['listed_ago']}

Write three captions:
1. YOUTUBE: Max 100 chars. Punchy. End with call-to-action. Include 3-5 hashtags on a new line.
2. INSTAGRAM: Max 220 chars. Emoji-rich, collector-focused. Include 10 hashtags on a new line.
3. FACEBOOK: Max 280 chars. Informative, price-forward. No hashtags.

Respond ONLY with valid JSON in this exact format:
{{
  "youtube": {{ "caption": "...", "hashtags": ["...", "..."] }},
  "instagram": {{ "caption": "...", "hashtags": ["...", "..."] }},
  "facebook": {{ "caption": "..." }}
}}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def main():
    print("=" * 55)
    print("STAGE 2 — COPYWRITER")
    print("=" * 55)

    # Load stage1 manifests
    with open("flywheel_test_output/stage1_manifests.json", "r", encoding="utf-8") as f:
        manifests = json.load(f)

    print(f"\n[OK] Loaded {len(manifests)} manifests from Stage 1")

    results = []
    for i, card in enumerate(manifests, 1):
        print(f"\n[{i}/{len(manifests)}] Processing: {card['title'][:50]}")

        # QA check (skipped in test — no real video)
        print(f"  [QA] Skipped in test mode (no Veo video rendered yet)")
        card["qa_passed"] = True
        card["qa_notes"] = "Test mode — QA skipped"

        # Generate captions
        print(f"  [GEMINI] Generating captions...")
        try:
            captions = await asyncio.to_thread(
                lambda c=card: asyncio.run(generate_captions(c))
            )
            card["captions"] = captions
            card["status"] = "ready_to_publish"

            print(f"  [OK] YouTube : {captions['youtube']['caption'][:70]}")
            print(f"  [OK] Instagram: {captions['instagram']['caption'][:70]}")
            print(f"  [OK] Facebook : {captions['facebook']['caption'][:70]}")
        except Exception as e:
            print(f"  [ERROR] Caption generation failed: {e}")
            card["status"] = "qa_failed"
            card["qa_notes"] = str(e)

        results.append(card)

    # Save stage2 output
    os.makedirs("flywheel_test_output", exist_ok=True)
    with open("flywheel_test_output/stage2_manifests.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ready = [c for c in results if c["status"] == "ready_to_publish"]
    print(f"\n[SAVED] -> flywheel_test_output/stage2_manifests.json")
    print(f"[STAGE 2 STATUS] COMPLETE — {len(ready)}/{len(results)} ready to publish")
    print("=" * 55)

if __name__ == "__main__":
    asyncio.run(main())
