---
name: Broadcaster
description: Reads publish-ready manifests from gs://ready-bucket, then uploads the final video and platform-specific captions to YouTube Shorts, Instagram Reels, and Facebook Reels. Updates the manifest status after each successful post.
---

# Broadcaster Skill

## Overview

The Broadcaster skill is the **third and final stage** of the content flywheel. It reads every manifest with `status: "ready_to_publish"` from GCS, downloads the final video, and distributes it to YouTube Shorts, Instagram, and Facebook using their respective APIs.

---

## Step 1 — Load Ready Manifests from GCS

```python
from google.cloud import storage
import json

client = storage.Client()
bucket = client.bucket("ready-bucket")
blobs = bucket.list_blobs(prefix="queue/")

ready = []
for blob in blobs:
    if blob.name.endswith("manifest.json"):
        manifest = json.loads(blob.download_as_text())
        if manifest.get("status") == "ready_to_publish":
            ready.append((blob.name, manifest))
```

For each manifest, download the video to a local temp file:
```python
video_blob = bucket.blob(manifest["video_uri"].replace("gs://ready-bucket/", ""))
video_blob.download_to_filename(f"/tmp/{card_id}.mp4")
```

---

## Step 2 — Detect Available Platforms

Before attempting any upload, check which platforms have credentials configured. **Platforms with missing credentials are skipped automatically — no error is raised.**

```python
import os

platforms_enabled = {}

# YouTube: needs both secrets file path and token file path
yt_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS")
yt_token   = os.getenv("YOUTUBE_TOKEN")
if yt_secrets and yt_token and os.path.exists(yt_secrets) and os.path.exists(yt_token):
    platforms_enabled["youtube"] = True
else:
    print("[SKIP] YouTube — YOUTUBE_CLIENT_SECRETS or YOUTUBE_TOKEN not set/found")

# Instagram: needs user ID + access token
ig_user  = os.getenv("IG_USER_ID")
ig_token = os.getenv("IG_ACCESS_TOKEN")
if ig_user and ig_token:
    platforms_enabled["instagram"] = True
else:
    print("[SKIP] Instagram — IG_USER_ID or IG_ACCESS_TOKEN not set")

# Facebook: needs page ID + page token
fb_page  = os.getenv("FB_PAGE_ID")
fb_token = os.getenv("FB_PAGE_TOKEN")
if fb_page and fb_token:
    platforms_enabled["facebook"] = True
else:
    print("[SKIP] Facebook — FB_PAGE_ID or FB_PAGE_TOKEN not set")

if not platforms_enabled:
    print("[ABORT] No platforms configured. Set at least one platform's credentials.")
    # Update manifest and exit
    manifest["status"] = "publish_skipped"
    manifest["skip_reason"] = "No platform credentials configured"
    # write manifest back to GCS ...
    continue
```

---

## Step 3 — Upload to YouTube Shorts (if enabled)

```python
if platforms_enabled.get("youtube"):
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials

        youtube_creds = Credentials.from_authorized_user_file(yt_token)
        youtube = build("youtube", "v3", credentials=youtube_creds)

        yt_caption = manifest["captions"]["youtube"]
        full_description = yt_caption["caption"] + "\n\n" + " ".join(yt_caption["hashtags"])

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": manifest["title"][:100],
                    "description": full_description,
                    "tags": [h.lstrip("#") for h in yt_caption["hashtags"]],
                    "categoryId": "26",  # Howto & Style
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                    "madeForKids": False,
                },
            },
            media_body=MediaFileUpload(f"/tmp/{card_id}.mp4", chunksize=-1, resumable=True),
        )
        response = None
        while response is None:
            _, response = request.next_chunk()

        platform_ids["youtube"] = f"https://www.youtube.com/shorts/{response['id']}"
        print(f"[OK] YouTube → {platform_ids['youtube']}")
    except Exception as e:
        print(f"[ERROR] YouTube upload failed: {e}")
        platform_ids["youtube"] = f"error: {e}"
```

> **Shorts requirement:** the video must be vertical (9:16) and ≤ 60 seconds. The Producer skill already ensures this.

---

## Step 4 — Upload to Instagram Reels (if enabled)

```python
if platforms_enabled.get("instagram"):
    try:
        import requests, time

        ig_caption = manifest["captions"]["instagram"]
        full_ig_caption = ig_caption["caption"] + "\n\n" + " ".join(ig_caption["hashtags"])

        # Step A: Create media container
        container_resp = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_user}/media",
            data={
                "media_type": "REELS",
                "video_url": manifest["video_uri_public"],  # public HTTPS URL
                "caption": full_ig_caption,
                "share_to_feed": True,
                "access_token": ig_token,
            }
        ).json()
        container_id = container_resp["id"]

        # Step B: Poll until FINISHED
        for _ in range(30):
            status_resp = requests.get(
                f"https://graph.facebook.com/v19.0/{container_id}",
                params={"fields": "status_code", "access_token": ig_token}
            ).json()
            if status_resp.get("status_code") == "FINISHED":
                break
            time.sleep(10)

        # Step C: Publish
        publish_resp = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_user}/media_publish",
            data={"creation_id": container_id, "access_token": ig_token}
        ).json()
        platform_ids["instagram"] = publish_resp["id"]
        print(f"[OK] Instagram → media_id={platform_ids['instagram']}")
    except Exception as e:
        print(f"[ERROR] Instagram upload failed: {e}")
        platform_ids["instagram"] = f"error: {e}"
```

> **Note:** `video_uri_public` must be a publicly accessible HTTPS URL. Sign a temporary GCS URL or copy the video to a public CDN path before posting.

---

## Step 5 — Upload to Facebook Reels (if enabled)

```python
if platforms_enabled.get("facebook"):
    try:
        import requests

        fb_caption = manifest["captions"]["facebook"]["caption"]

        # Step A: Initialize upload session
        init_resp = requests.post(
            f"https://graph.facebook.com/v19.0/{fb_page}/video_reels",
            data={"upload_phase": "start", "access_token": fb_token}
        ).json()
        video_id  = init_resp["video_id"]
        upload_url = init_resp["upload_url"]

        # Step B: Upload bytes
        with open(f"/tmp/{card_id}.mp4", "rb") as f:
            file_size = os.path.getsize(f"/tmp/{card_id}.mp4")
            requests.post(upload_url, data=f, headers={
                "Authorization": f"OAuth {fb_token}",
                "offset": "0",
                "file_size": str(file_size),
            })

        # Step C: Publish
        requests.post(
            f"https://graph.facebook.com/v19.0/{fb_page}/video_reels",
            data={
                "video_id": video_id,
                "upload_phase": "finish",
                "video_state": "PUBLISHED",
                "description": fb_caption,
                "access_token": fb_token,
            }
        )
        platform_ids["facebook"] = video_id
        print(f"[OK] Facebook → video_id={video_id}")
    except Exception as e:
        print(f"[ERROR] Facebook upload failed: {e}")
        platform_ids["facebook"] = f"error: {e}"
```

---

## Step 6 — Update Manifest Status

```python
published_count = sum(1 for v in platform_ids.values() if not str(v).startswith("error"))
skipped_count   = len([p for p in ["youtube","instagram","facebook"] if p not in platforms_enabled])

if published_count == 0:
    final_status = "publish_failed"
elif published_count < len(platforms_enabled):
    final_status = "publish_partial"
else:
    final_status = "published"

manifest.update({
    "status": final_status,
    "published_at": datetime.now(timezone.utc).isoformat(),
    "platforms_attempted": list(platforms_enabled.keys()),
    "platforms_skipped": [p for p in ["youtube","instagram","facebook"] if p not in platforms_enabled],
    "platform_ids": platform_ids,
})
# write manifest back to GCS ...
```

**Status meanings:**

| Status | Meaning |
|---|---|
| `published` | ✅ All configured platforms succeeded |
| `publish_partial` | ⚠️ Some configured platforms failed — check `platform_ids` |
| `publish_failed` | ❌ All configured platforms failed |
| `publish_skipped` | ⚠️ No credentials configured at all |

---

## Environment Variables

All platform credentials are **optional** — missing ones are safely skipped.

| Variable | Platform | Required? |
|---|---|---|
| `GCS_BUCKET` | GCS | ✅ Always |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCS / Veo | ✅ Always |
| `YOUTUBE_CLIENT_SECRETS` | YouTube | Optional |
| `YOUTUBE_TOKEN` | YouTube | Optional |
| `IG_USER_ID` | Instagram | Optional |
| `IG_ACCESS_TOKEN` | Instagram | Optional |
| `FB_PAGE_ID` | Facebook | Optional |
| `FB_PAGE_TOKEN` | Facebook | Optional |

---

## Platform Requirements Summary

| Platform | Format | Max Duration | Aspect Ratio |
|---|---|---|---|
| YouTube Shorts | MP4 H.264 | 60s | 9:16 |
| Instagram Reels | MP4 H.264 | 90s | 9:16 |
| Facebook Reels | MP4 H.264 | 90s | 9:16 |
