---
name: Producer
description: Scans the TCG Nakama marketplace "Fresh Pulls" endpoint for cards priced above $50 (¥7,500), then uses Gemini + Veo to generate a 9:16 animated background loop and composites the card image on top, producing a short-form video asset ready for QA and publishing.
---

# Producer Skill

## Overview

The Producer skill is the **first stage** of the content flywheel. It monitors the Fresh Pulls section of the marketplace, selects qualifying cards, and generates polished 9:16 short-form video assets for each.

---

## Step 1 — Scan Fresh Pulls for Qualifying Cards

Call the internal marketplace endpoint to retrieve the current Fresh Pulls list.

```
GET http://localhost:8000/
```

From the rendered `fresh_pulls` context, extract every product where:
- `price >= 50` (USD) **or** `price >= 7500` (JPY)
- `totalInventory > 0` (in stock only)

For each qualifying card, collect:
```json
{
  "id": "gid://shopify/Product/...",
  "title": "モンキー・D・ルフィ",
  "price": 285,
  "rarity": "Ultra Rare",
  "set": "ST10",
  "card_number": "ST10-006",
  "image": "https://cdn.shopify.com/...",
  "listed_ago": "NEW ARRIVAL"
}
```

---

## Step 2 — Generate 9:16 Background Loop with Veo

For each qualifying card, craft a Veo video generation prompt that matches the card's theme.

**Prompt formula:**
```
A cinematic, looping 9:16 vertical video background for a trading card featuring {card_title}.
Theme: {derived_from_set_and_rarity}.
Style: dark, atmospheric, holographic light shards, slow particle drift, no text, no faces.
Duration: 6 seconds, seamless loop. Aspect ratio: 9:16.
```

**Derive theme from card metadata:**
| Set / Game | Theme hint |
|---|---|
| One Piece | ocean storm, Straw Hat crew silhouettes, sea foam |
| Pokémon | electro-sparks, forest mist, stadium lights |
| Magic: TG | arcane runes, elemental energy, dark library |
| Yu-Gi-Oh! | ancient stone pillars, blue starfield, monster shadows |

**API call — Veo via Vertex AI:**
```python
import vertexai
from vertexai.preview.vision_models import VideoGenerationModel

vertexai.init(project=PROJECT_ID, location="us-central1")
model = VideoGenerationModel.from_pretrained("veo-2.0-generate-001")

operation = model.generate_video(
    prompt=veo_prompt,
    aspect_ratio="9:16",
    duration_seconds=6,
    number_of_videos=1,
    output_gcs_uri=f"gs://ready-bucket/backgrounds/{card_id}/bg.mp4",
)
operation.result()  # blocks until complete
```

---

## Step 3 — Composite Card Overlay

Once the background render is complete, composite the card image over it using `ffmpeg`.

**Overlay spec:**
- Card image centred horizontally, positioned at 15% from the top
- Card width = 60% of video width, aspect ratio preserved
- Add a subtle drop-shadow filter
- Burn-in a semi-transparent bottom bar with card name, set, and price

```bash
ffmpeg -i gs_bg_local.mp4 \
       -i card_image.png \
       -filter_complex "[1:v]scale=iw*0.6:-1[card]; \
                        [0:v][card]overlay=(W-w)/2:H*0.15[out]; \
                        [out]drawtext=fontfile=/usr/share/fonts/NotoSansJP.ttf: \
                        text='{card_title} | {set} | ¥{price}': \
                        x=(W-tw)/2:y=H*0.88:fontsize=28:fontcolor=white: \
                        box=1:boxcolor=black@0.55:boxborderw=12" \
       -map "[out]" -map 0:a? \
       -c:v libx264 -preset fast -crf 22 -an \
       output.mp4
```

---

## Step 4 — Save Manifest to GCS

After rendering, write a JSON manifest per card to Google Cloud Storage.

**Output path:** `gs://ready-bucket/queue/{card_id}/manifest.json`

```json
{
  "card_id": "gid://shopify/Product/...",
  "title": "モンキー・D・ルフィ",
  "price_jpy": 285,
  "rarity": "Ultra Rare",
  "set": "ST10-006",
  "video_uri": "gs://ready-bucket/queue/{card_id}/final.mp4",
  "bg_uri": "gs://ready-bucket/backgrounds/{card_id}/bg.mp4",
  "card_image_url": "https://cdn.shopify.com/...",
  "status": "pending_qa",
  "produced_at": "2026-02-20T15:31:50+09:00"
}
```

---

## Expected Outputs

| Asset | GCS Path |
|---|---|
| Background loop | `gs://ready-bucket/backgrounds/{card_id}/bg.mp4` |
| Final composite | `gs://ready-bucket/queue/{card_id}/final.mp4` |
| Manifest | `gs://ready-bucket/queue/{card_id}/manifest.json` |

---

## Environment Variables Required

| Variable | Description |
|---|---|
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCS_BUCKET` | GCS bucket name (default: `ready-bucket`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON |
