---
name: Copywriter
description: Runs Vision AI QA on the produced video to verify card name accuracy and detect glitches, then uses Gemini to write platform-optimised captions for YouTube Shorts, Instagram, and Facebook. Saves a final publish-ready JSON package to gs://ready-bucket.
---

# Copywriter Skill

## Overview

The Copywriter skill is the **second stage** of the content flywheel. It takes each produced video from the Producer skill, quality-checks it with Gemini Vision, and generates platform-optimised captions and hashtags before handing off to the Broadcaster.

---

## Step 1 — Load Manifest from GCS

Read all manifests with `status: "pending_qa"` from the GCS queue:

```python
from google.cloud import storage

client = storage.Client()
bucket = client.bucket("ready-bucket")
blobs = bucket.list_blobs(prefix="queue/")

pending = []
for blob in blobs:
    if blob.name.endswith("manifest.json"):
        manifest = json.loads(blob.download_as_text())
        if manifest.get("status") == "pending_qa":
            pending.append(manifest)
```

---

## Step 2 — Vision AI QA Check

For each manifest, download the composite video and extract 3 key frames (start, middle, end). Send each frame to Gemini's vision model for QA.

**Frame extraction:**
```bash
ffmpeg -i final.mp4 -vf "select='eq(n\,0)+eq(n\,45)+eq(n\,89)'" \
       -vsync 0 frame_%02d.png
```

**Gemini Vision QA prompt (per frame):**
```
You are a QA reviewer for a trading card marketing video.

Card expected: "{title}" from set "{set}", card number "{card_number}".

Inspect this video frame and report:
1. Is the card image clearly visible and undistorted? (yes/no)
2. Does the on-screen text match "{title}" and "¥{price}"? (yes/no/not visible)
3. Are there any rendering glitches, black frames, or compression artifacts? (yes/no)
4. Is the background animated and atmospheric (not static)? (yes/no)

Respond in JSON: { "card_visible": bool, "text_accurate": bool, "glitches": bool, "background_animated": bool, "notes": "..." }
```

**QA decision logic:**
```python
# Pass if ALL three frames pass these thresholds:
qa_pass = (
    results["card_visible"] == True and
    results["text_accurate"] == True and
    results["glitches"] == False
)
```

If QA fails → update manifest `status: "qa_failed"` and log `qa_notes`. Stop processing this card.

---

## Step 3 — Write Platform Captions with Gemini

For each video that passes QA, generate captions for all three platforms.

**Gemini prompt:**
```
You are a TCG trading card content creator writing short-form social media captions.

Card details:
- Name: {title} (Japanese: {title_ja if available})
- Set: {set} | Card Number: {card_number}
- Rarity: {rarity}
- Price: ¥{price}
- Freshness: {listed_ago}

Write three captions:

1. YOUTUBE_SHORTS: Max 100 chars. Punchy opener. End with a call-to-action.
   Include 3-5 relevant hashtags on a new line.

2. INSTAGRAM: Max 220 chars. Conversational, emoji-rich, collector-focused.
   Include 10-15 hashtags on a new line.

3. FACEBOOK: Max 280 chars. Informative, price-forward, link-friendly.
   No hashtags needed.

Respond in JSON:
{
  "youtube": { "caption": "...", "hashtags": ["...", "..."] },
  "instagram": { "caption": "...", "hashtags": ["...", "..."] },
  "facebook": { "caption": "..." }
}
```

**Hashtag seed list to include where relevant:**
`#TCG #TradingCards #Onepiece #Pokemon #tcgnakama #FreshPulls #CardCollector #投資 #トレカ #カード`

---

## Step 4 — Save Publish-Ready JSON to GCS

Update the manifest with QA results and captions, then write the final package:

**Output path:** `gs://ready-bucket/queue/{card_id}/manifest.json` (overwrite)

```json
{
  "card_id": "...",
  "title": "...",
  "price_jpy": 285,
  "rarity": "Ultra Rare",
  "set": "ST10-006",
  "video_uri": "gs://ready-bucket/queue/{card_id}/final.mp4",
  "status": "ready_to_publish",
  "qa_passed": true,
  "qa_notes": "All frames clear. Text accurate.",
  "captions": {
    "youtube": {
      "caption": "🔥 NEW PULL! Luffy ST10 just dropped — grab it before it's gone!",
      "hashtags": ["#TCG", "#OnePiece", "#FreshPulls", "#tcgnakama"]
    },
    "instagram": {
      "caption": "🃏✨ Fresh out the pack! Monkey D. Luffy ST10 hitting the vault at ¥285. Collector's dream fr 🔥",
      "hashtags": ["#TCG", "#OnePiece", "#Pokemon", "#CardCollector", "#FreshPulls", "#tcgnakama", "#トレカ", "#カード", "#投資", "#ワンピースカード"]
    },
    "facebook": {
      "caption": "New arrival: Monkey D. Luffy (ST10-006) — Ultra Rare — now listed at ¥285. In stock now at TCGNakama.com. Limited quantity!"
    }
  },
  "produced_at": "2026-02-20T15:31:50+09:00",
  "copywritten_at": "2026-02-20T15:35:00+09:00"
}
```

---

## Expected Outputs

| Asset | GCS Path |
|---|---|
| Updated manifest (pass) | `gs://ready-bucket/queue/{card_id}/manifest.json` → `status: ready_to_publish` |
| Updated manifest (fail) | `gs://ready-bucket/queue/{card_id}/manifest.json` → `status: qa_failed` |
| QA frames | `gs://ready-bucket/queue/{card_id}/frame_*.png` |

---

## Environment Variables Required

| Variable | Description |
|---|---|
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCS_BUCKET` | GCS bucket name (default: `ready-bucket`) |
| `GEMINI_MODEL` | Model to use (default: `gemini-2.0-flash`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON |
