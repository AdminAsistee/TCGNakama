---
description: Content flywheel — scans Fresh Pulls for high-value cards, generates short-form video assets, QA-checks them, writes captions, and publishes to YouTube Shorts, Instagram Reels, and Facebook Reels.
---

# Flywheel Workflow

Runs three skills in sequence: **Producer → Copywriter → Broadcaster**.

Each stage reads/writes manifests at `gs://ready-bucket/queue/{card_id}/manifest.json` using the `status` field as a handoff signal.

---

## Pre-flight Checks

Before running, confirm the following environment variables are set:

```
GCP_PROJECT_ID
GCS_BUCKET=ready-bucket
GOOGLE_APPLICATION_CREDENTIALS
YOUTUBE_CLIENT_SECRETS
YOUTUBE_TOKEN
IG_USER_ID
IG_ACCESS_TOKEN
FB_PAGE_ID
FB_PAGE_TOKEN
```

Also confirm the app is running locally or the Fresh Pulls endpoint is reachable:
```
curl http://localhost:8000/
```

---

## Stage 1 — Producer

**Skill:** `.agent/skills/producer/SKILL.md`

**What it does:**
- Fetches Fresh Pulls from the marketplace (`GET /`)
- Filters cards where `price >= ¥7,500` and `totalInventory > 0`
- For each qualifying card, generates a Veo 9:16 background loop and composites the card image overlay using ffmpeg
- Writes `manifest.json` with `status: "pending_qa"` to `gs://ready-bucket/queue/{card_id}/`

**Run the Producer skill now. Continue only after all manifests are written to GCS with `status: "pending_qa"`.**

---

## Stage 2 — Copywriter

**Skill:** `.agent/skills/copywriter/SKILL.md`

**What it does:**
- Reads all manifests with `status: "pending_qa"` from `gs://ready-bucket/queue/`
- Extracts 3 frames per video and runs Gemini Vision QA
  - If QA fails → sets `status: "qa_failed"`, skips the card
  - If QA passes → continues
- Calls Gemini to generate platform captions for YouTube, Instagram, and Facebook
- Overwrites the manifest with `status: "ready_to_publish"` and the full `captions` object

**Run the Copywriter skill now. Continue only after all passing manifests have `status: "ready_to_publish"`.**

> Cards with `status: "qa_failed"` are skipped automatically. Review them in GCS afterwards.

---

## Stage 3 — Broadcaster

**Skill:** `.agent/skills/broadcaster/SKILL.md`

**What it does:**
- Reads all manifests with `status: "ready_to_publish"` from `gs://ready-bucket/queue/`
- Downloads each video from GCS
- Uploads to **YouTube Shorts**, **Instagram Reels**, and **Facebook Reels** using their Graph / Data APIs
- Updates each manifest to `status: "published"` with platform URLs and IDs

**Run the Broadcaster skill now.**

---

## Post-Run Summary

After all three stages complete, check the GCS bucket for final manifest statuses:

| Status | Meaning |
|---|---|
| `published` | ✅ Successfully posted to all platforms |
| `publish_partial` | ⚠️ Posted to some platforms — check `platform_ids` for details |
| `qa_failed` | ❌ Video did not pass QA — re-run Producer for this card |
| `pending_qa` | 🕐 Copywriter has not yet processed this card |

---

## Re-running a Single Card

To re-run just one card (e.g. after a QA failure), set its manifest `status` back to `"pending_qa"` in GCS and run Stage 2 and Stage 3 only.
