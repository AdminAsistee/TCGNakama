"""
Pollo.ai test — submit and wait, then probe for status endpoint
"""
import io, sys, os, json, time, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import httpx
except ImportError:
    os.system("pip install httpx -q")
    import httpx

API_KEY  = "pollo_OZkayR2Nr9vNiYjG9UgABXKzoIrdTCUQvkkj9GBnVRM9"
OUT_PATH = "flywheel_test_output/videos/pollo_test_bg.mp4"
os.makedirs("flywheel_test_output/videos", exist_ok=True)

HEADERS = {"Content-Type": "application/json", "x-api-key": API_KEY}

# ── Submit ────────────────────────────────────────────────
print("=" * 50)
print("POLLO.AI TEST")
print("=" * 50)
print("\n[1] Submitting generation...")

resp = httpx.post(
    "https://pollo.ai/api/platform/generation/sora/sora-2",
    headers=HEADERS,
    json={
        "input": {
            "prompt": (
                "Cinematic vertical background for a TCG trading card game showcase. "
                "Deep navy and purple tones, glowing bokeh particles, soft light streaks. "
                "No text, no cards, no characters. 9:16 vertical."
            ),
            "aspectRatio": "9:16",
            "length": 4,
        }
    },
    timeout=30
)
data    = resp.json()
task_id = data.get("data", {}).get("taskId")
print(f"  HTTP {resp.status_code} | taskId: {task_id}")

# ── Wait for generation ───────────────────────────────────
WAIT = 90
print(f"\n[2] Waiting {WAIT}s for Sora-2 to generate...")
for i in range(WAIT, 0, -10):
    print(f"  {i}s remaining...", end="\r")
    time.sleep(10)
print()

# ── Probe status endpoints ────────────────────────────────
print(f"\n[3] Probing status endpoints for taskId={task_id}...")
PROBES = [
    f"https://pollo.ai/api/platform/generation/{task_id}",
    f"https://pollo.ai/api/platform/generation/result/{task_id}",
    f"https://pollo.ai/api/platform/generation/sora/{task_id}",
    f"https://pollo.ai/api/platform/generation/status/{task_id}",
    f"https://pollo.ai/api/platform/generation/task/{task_id}",
    f"https://pollo.ai/api/platform/task/{task_id}",
    f"https://pollo.ai/api/platform/result/{task_id}",
    f"https://pollo.ai/api/generation/{task_id}",
    f"https://pollo.ai/api/task/{task_id}",
    f"https://pollo.ai/api/platform/generation?taskId={task_id}",
    f"https://pollo.ai/api/platform/generation/list?taskId={task_id}",
]

video_url = None
for url in PROBES:
    r = httpx.get(url, headers=HEADERS, timeout=10)
    body = r.text[:200]
    print(f"  {r.status_code}  {url}")
    if r.status_code == 200:
        print(f"       -> {body}")
        d = r.json()
        result = d.get("result", [])
        if result:
            video_url = result[0].get("videoUrl")
            print(f"\n  [FOUND] videoUrl: {video_url}")
            break

if not video_url:
    print("\n[INFO] Could not retrieve via GET — check your Pollo dashboard for the video URL:")
    print(f"       https://pollo.ai  (taskId: {task_id})")
    sys.exit(0)

# ── Download ──────────────────────────────────────────────
print(f"\n[4] Downloading...")
urllib.request.urlretrieve(video_url, OUT_PATH)
mb = os.path.getsize(OUT_PATH) / 1024 / 1024
print(f"  Saved -> {OUT_PATH} ({mb:.1f} MB)")
print("\nDONE!")

import subprocess
subprocess.Popen(["explorer", "/select,", os.path.abspath(OUT_PATH)])
