"""
TCG Nakama — New Cards Showcase
- Blurry-first-card animated intro (no logo, no text banner)
- Per-card: Gemini analyzes card image → unique cinematic prompt
- Per-card: Sora-2 generates unique background video (no audio)
- ffmpeg composites card + text on its own background
- xfade concat → one final video uploaded to GCS
"""
import io, sys, os, re, json, time, asyncio, subprocess, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import httpx
except ImportError:
    os.system("pip install httpx -q")
    import httpx

from dotenv import load_dotenv
load_dotenv(override=True)
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────
GCP_PROJECT       = os.getenv("GCP_PROJECT_ID", "tcgnakama")
GCS_BUCKET        = os.getenv("GCS_BUCKET", "ready-bucket")
POLLO_KEY         = os.getenv("POLLO_API_KEY", "")
GEMINI_KEY        = os.getenv("GEMINI_API_KEY")
ZAPIER_WEBHOOK    = os.getenv("ZAPIER_SHOWCASE_WEBHOOK_URL", "")  # showcase video → Facebook
OUTPUT_DIR        = "flywheel_test_output/videos"
CARD_LIMIT        = 3
INTRO_SEC         = 3       # blurry-card intro duration
CARD_SEC          = 5
XFADE_SEC         = 0.5
BG_W, BG_H        = 720, 1280
os.makedirs(OUTPUT_DIR, exist_ok=True)

POLLO_HEADERS = {"Content-Type": "application/json", "x-api-key": POLLO_KEY}

# Windows: add WinGet ffmpeg install to PATH
if os.name == 'nt':
    _win_ffmpeg = (os.getenv("LOCALAPPDATA","") +
                   r"\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin")
    if _win_ffmpeg and _win_ffmpeg not in os.environ.get("PATH",""):
        os.environ["PATH"] = os.environ.get("PATH","") + ";" + _win_ffmpeg


def ensure_ffmpeg():
    """
    On Linux servers, ensure the full static ffmpeg build is available.
    Validates the cached binary before using it; re-downloads if corrupt.
    Raises RuntimeError if ffmpeg cannot be made available.
    """
    if os.name == 'nt':
        return  # Windows handled above via PATH

    _bin  = "/tmp/ffmpeg_static/ffmpeg"
    _dir  = "/tmp/ffmpeg_static"
    _url  = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    _tar  = "/tmp/ffmpeg.tar.xz"

    def _prepend_path():
        _p = os.environ.get("PATH", "")
        if _dir not in _p:
            os.environ["PATH"] = _dir + ":" + _p

    def _valid():
        """Return True if the cached binary runs successfully."""
        import subprocess as _sp
        try:
            r = _sp.run([_bin, "-version"], capture_output=True, timeout=10)
            return r.returncode == 0
        except Exception:
            return False

    # Check cached binary
    if os.path.exists(_bin):
        if _valid():
            _prepend_path()
            print("[ffmpeg] Using cached static binary ✓")
            return
        else:
            print("[ffmpeg] Cached binary invalid — re-downloading...")
            import shutil as _sh
            _sh.rmtree(_dir, ignore_errors=True)

    # Download
    print("[ffmpeg] Downloading static binary (~40 MB)...")
    import tarfile, urllib.request as _u
    try:
        _u.urlretrieve(_url, _tar)
        os.makedirs(_dir, exist_ok=True)
        with tarfile.open(_tar, "r:xz") as t:
            for m in t.getmembers():
                if m.name.endswith("/ffmpeg") or m.name == "ffmpeg":
                    m.name = "ffmpeg"
                    t.extract(m, _dir)
                    break
        os.chmod(_bin, 0o755)
        if not _valid():
            raise RuntimeError("Downloaded binary failed validation")
        _prepend_path()
        print("[ffmpeg] Static binary ready ✓")
    except Exception as _e:
        raise RuntimeError(f"[ffmpeg] Could not install ffmpeg: {_e}") from _e



# Font for ffmpeg drawtext — explicit fontfile avoids fontconfig failures on minimal containers
if os.name == 'nt':
    FONT_PATH = ""  # Windows: ffmpeg finds fonts via fontconfig automatically
else:
    # Linux: prefer DejaVu (installed via Aptfile), fall back to any available font
    _font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    FONT_PATH = next((f for f in _font_candidates if os.path.exists(f)), "")


# ── Helpers ───────────────────────────────────────────────
def safe(s):    return re.sub(r"['\:\\#@\[\]{}()]", "", str(s or ""))
def eng(title):
    m = re.search(r'\(([^)]+)\)', title)
    return (m.group(1) if m else title.split(' - ')[0])[:24]
def accent(rarity):
    r = (rarity or '').lower()
    if 'secret' in r: return "0xFFD700"
    if 'ultra'  in r: return "0xE040FB"
    if 'rare'   in r: return "0x40C4FF"
    return "0xFFFFFF"


# ── GCS ──────────────────────────────────────────────────
def get_gcs():
    from google.cloud import storage
    c = storage.Client(project=GCP_PROJECT)
    try: c.get_bucket(GCS_BUCKET)
    except: c.create_bucket(GCS_BUCKET, location="US")
    return c

def gcs_upload(client, local, remote):
    blob = client.bucket(GCS_BUCKET).blob(remote)
    blob.upload_from_filename(local)
    blob.make_public()
    public_url = blob.public_url
    print(f"  [GCS] gs://{GCS_BUCKET}/{remote}")
    print(f"  [URL] {public_url}")
    return f"gs://{GCS_BUCKET}/{remote}", public_url


# ── Shopify ───────────────────────────────────────────────
async def get_fresh_pulls():
    from app.dependencies import ShopifyClient
    products = await ShopifyClient().get_products()
    in_stock = [p for p in products if p.get('totalInventory', 0) > 0]
    return sorted(in_stock, key=lambda x: x.get('createdAt',''), reverse=True)[:CARD_LIMIT]


# ── Gemini: per-card analysis ─────────────────────────────
def analyze_card(image_path: str, card_title: str, idx: int) -> dict:
    """Analyze ONE card image with Gemini → unique cinematic prompt."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_KEY)

    prompt = f"""Analyze this TCG card image (title: "{card_title}").

Return ONLY this JSON (no extra text):
{{
  "name": "English card name (short, e.g. Chien-Pao or Houndstone)",
  "type": "Element type (Fire/Water/Electric/Ice/Grass/Psychic/Ghost/Dragon/Dark/Steel/Normal)",
  "motion": "Describe in max 2 sentences ONLY the character's animation motion. Focus on what the creature physically does (shimmers, erupts, floats, crackles). Do NOT mention the card frame, text, or any instruction to keep things static.",
  "accent_color": "#RRGGBB hex that fits the card theme",
  "intro_word": "One dramatic single word (e.g. FROZEN / ABLAZE / HAUNTED / ELECTRIC)"
}}"""

    try:
        with open(image_path, 'rb') as f: data = f.read()
        ext  = image_path.rsplit('.',1)[-1].lower()
        mime = f"image/{ext}" if ext in ('png','webp','gif') else "image/jpeg"

        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=data, mime_type=mime),
                types.Part.from_text(text=prompt),
            ]
        )
        text = resp.text.strip()
        m    = re.search(r'\{.*\}', text, re.DOTALL)
        if m: return json.loads(m.group(0))
    except Exception as e:
        print(f"    [Gemini] Error: {e}")

    return {
        "name": eng(card_title), "type": "Normal",
        "motion": "subtle shimmer emanates from the character, holographic particles drift from its form",
        "accent_color": "#60A0FF", "intro_word": "REVEALED"
    }


# ── Pollo 1.6 per-card animated background ──────────────
doc_string = """Submit img2vid to Pollo v1.6, poll until done, normalise to 720×1280 (no audio)."""
def generate_bg(image_url: str, card_name: str, motion: str, out_path: str) -> str:
    raw_path = out_path.replace('.mp4', '_raw.mp4')

    # Grounding prompt — same 'THIS EXACT CARD' template that works well with img2vid
    grounded_prompt = (
        f"A 5-second animation of THIS EXACT CARD where ONLY {card_name} inside the card artwork "
        f"comes alive and moves. {motion}. "
        f"The card border, card name, HP number, attack names, damage numbers, weakness, resistance, "
        f"retreat cost, rarity symbol, and ALL printed text must stay completely frozen and unchanged. "
        f"No new elements. No camera movement. The card paper and borders are perfectly static."
    )
    print(f"    [Prompt] {grounded_prompt[:110]}...")

    resp = httpx.post(
        "https://pollo.ai/api/platform/generation/pollo/pollo-v1-6",
        headers=POLLO_HEADERS,
        json={"input": {"image": image_url, "prompt": grounded_prompt,
                        "resolution": "480p", "mode": "basic", "length": 5}},
        timeout=30
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Pollo-1.6 submission failed ({resp.status_code}): {resp.text}")

    task_id = resp.json().get("data", {}).get("taskId")
    if not task_id: raise RuntimeError(f"Submission failed: {resp.text}")
    print(f"[Pollo-1.6] taskId={task_id}", end=" ")

    deadline = time.time() + 360
    while time.time() < deadline:
        time.sleep(10)
        r = httpx.get(f"https://pollo.ai/api/platform/generation/{task_id}/status",
                      headers=POLLO_HEADERS, timeout=15)
        if r.status_code != 200: continue
        gens = r.json().get("data", {}).get("generations", [])
        if not gens: continue
        status = gens[0].get("status")
        url    = gens[0].get("url")
        print(".", end="", flush=True)
        if status == "succeed" and url:
            print(" done")
            urllib.request.urlretrieve(url, raw_path)
            vf = (f"scale={BG_W}:{BG_H}:force_original_aspect_ratio=decrease,"
                  f"pad={BG_W}:{BG_H}:(ow-iw)/2:(oh-ih)/2:black")
            subprocess.run([
                "ffmpeg","-y","-i", raw_path, "-vf", vf,
                "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p","-an",
                out_path
            ], capture_output=True)
            return out_path
        if status == "failed":
            raise RuntimeError("Pollo-1.6 generation failed")
    raise TimeoutError("Pollo-1.6 timed out")


# ── Gradient fallback bg ──────────────────────────────────
def gradient_bg(hex_color: str, out_path: str):
    r,g,b = int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16)
    subprocess.run([
        "ffmpeg","-y","-f","lavfi",
        "-i",f"color=c=0x0a0a1a:size={BG_W}x{BG_H}:rate=30",
        "-vf",f"geq=r='clip({r//8}+Y/30,0,{min(r,120)})':g='clip({g//8}+Y/35,0,{min(g,120)})':b='clip({b//8}+Y/20,0,{min(b,150)})',boxblur=20:1",
        "-t","5","-c:v","libx264","-pix_fmt","yuv420p","-an", out_path
    ], capture_output=True)


# ── Zapier webhook notification ───────────────────────────
def notify_zapier(manifest: dict):
    """
    POST key video info to the Zapier webhook so Zapier can upload
    the public_url video to Facebook (or any other platform).
    Silently skipped if ZAPIER_WEBHOOK_URL is not set.
    """
    if not ZAPIER_WEBHOOK:
        print("  [Zapier] ZAPIER_WEBHOOK_URL not set — skipping")
        return

    payload = {
        "video_url":    manifest["public_url"],
        "gcs_uri":      manifest["gcs_video_uri"],
        "generated_at": manifest["generated_at"],
        "card_count":   len(manifest["cards"]),
        "cards": [
            {
                "title": c["title"],
                "name":  c["name"],
                "type":  c["type"],
                "price_jpy": c["price"],
                "intro_word": c["word"],
            }
            for c in manifest["cards"]
        ],
        # Convenience fields Zapier can use directly in its Zap
        "caption": (
            "🃏 New cards just dropped at TCG Nakama!\n"
            + "\n".join(f"• {c['name']} ({c['type']}) — JPY {c['price']:,.0f}" for c in manifest["cards"])
            + "\n\nShop now 👉 tcgnakama.com"
        ),
    }

    try:
        resp = httpx.post(ZAPIER_WEBHOOK, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            print(f"  [Zapier] ✅ Webhook fired — status {resp.status_code}")
        else:
            print(f"  [Zapier] ⚠️  Unexpected status {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        print(f"  [Zapier] ❌ Failed to fire webhook: {e}")


# ── Intro: blurry first-card preview → unblur transition ─
def make_intro(first_card_img: str) -> str:
    """
    3-second intro: blurry first card image fades in, then lifts blur and fades to black.
    Uses two separate clips (heavy blur → lighter blur) xfaded together.
    Time-varying boxblur expressions are rejected by ffmpeg for looped still images,
    so we use static blur values per clip instead.
    """
    out   = f"{OUTPUT_DIR}/seg_intro.mp4"
    clip1 = f"{OUTPUT_DIR}/intro_heavy.mp4"
    clip2 = f"{OUTPUT_DIR}/intro_light.mp4"

    if first_card_img and os.path.exists(first_card_img):
        base = (
            f"scale={BG_W}:{BG_H}:force_original_aspect_ratio=increase,"
            f"crop={BG_W}:{BG_H},eq=brightness=-0.35"
        )
        # Clip 1: 2s heavy blur, fade in
        r1 = subprocess.run([
            "ffmpeg","-y","-loop","1","-framerate","30","-t","2","-i", first_card_img,
            "-vf", f"{base},boxblur=40:1,fade=in:st=0:d=0.5",
            "-t","2","-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p","-an", clip1
        ], capture_output=True, text=True)
        # Clip 2: 1.5s lighter blur, fade to black
        r2 = subprocess.run([
            "ffmpeg","-y","-loop","1","-framerate","30","-t","1.5","-i", first_card_img,
            "-vf", f"{base},boxblur=10:1,fade=out:st=0.9:d=0.6",
            "-t","1.5","-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p","-an", clip2
        ], capture_output=True, text=True)

        ok1 = r1.returncode == 0 and os.path.exists(clip1) and os.path.getsize(clip1) > 1000
        ok2 = r2.returncode == 0 and os.path.exists(clip2) and os.path.getsize(clip2) > 1000
        if ok1 and ok2:
            r3 = subprocess.run([
                "ffmpeg","-y","-i", clip1,"-i", clip2,
                "-filter_complex","[0:v][1:v]xfade=transition=fade:offset=1.5:duration=0.5[outv]",
                "-map","[outv]","-an",
                "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p", out
            ], capture_output=True, text=True)
            if r3.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 1000:
                return out
            print(f"  [intro xfade warn] {r3.stderr[-150:]}")
        else:
            print(f"  [intro clip warn] r1={r1.returncode} r2={r2.returncode}")
            if r1.stderr: print(f"    clip1: {r1.stderr[-100:]}")

    # Fallback: plain dark fade-in
    subprocess.run([
        "ffmpeg","-y","-f","lavfi",
        "-i", f"color=c=0x050510:size={BG_W}x{BG_H}:rate=30",
        "-vf", f"fade=in:st=0:d=0.5,fade=out:st={INTRO_SEC-0.5}:d=0.5",
        "-t", str(INTRO_SEC),
        "-c:v","libx264","-pix_fmt","yuv420p","-an", out
    ], capture_output=True)
    return out





# ── Per-card segment ──────────────────────────────────────
def make_card_segment(bg_path: str, img_path: str, card: dict, analysis: dict, idx: int) -> str:
    """
    Layout (consistent for every card):
      [0:v] bg_path  — Pollo 1.6 animated card video, streamed as backdrop (720x1280)
      [1:v] img_path — static card PNG, scaled to CARD_W=450px, slides up from bottom
    Text overlays fade in below the card.
    """
    seg    = f"{OUTPUT_DIR}/seg_{idx:02d}.mp4"
    name   = safe(analysis.get("name") or eng(card['title']))
    price  = f"JPY {card['price']:,.0f}"
    rar    = safe(card.get('rarity') or 'IN STOCK').upper()
    a      = accent(card.get('rarity'))
    word   = safe(analysis.get("intro_word","REVEALED")).upper()
    CARD_W = 450   # fixed card overlay width — ensures uniform sizing across all segments

    has_bg  = bg_path  and os.path.exists(bg_path)  and os.path.getsize(bg_path)  > 1000
    has_img = img_path and os.path.exists(img_path)

    # Sanity check: verify ffmpeg has drawtext available
    _fc_check = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
    if "drawtext" not in _fc_check.stdout:
        raise RuntimeError(f"drawtext filter not available! ffmpeg filters:\n{_fc_check.stdout[:500]}")

    # Explicit fontfile= required on Linux — fontconfig fails on minimal containers
    _ff = f"fontfile={FONT_PATH}:" if FONT_PATH else ""

    if has_bg and has_img:
        # ── PRIMARY: animated Pollo bg + static card overlay at fixed width ──
        # Card slides up from bottom, settles at vertical center minus small offset.
        # Use if() instead of max() for the y expression to avoid comma-parsing issues.
        slide_y = "if(lt(t\\,0.55)\\,(H-h)/2-80+(H+200)*(1-t/0.45)\\,(H-h)/2-80)"
        fc = (
            # bg: stream-loop Pollo video as full-frame backdrop
            f"[0:v]scale={BG_W}:{BG_H}:force_original_aspect_ratio=decrease,"
            f"pad={BG_W}:{BG_H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fade=in:st=0:d=0.35[bg];"

            # card: scale to fixed CARD_W, slide up + fade in
            f"[1:v]scale={CARD_W}:-1,format=rgba[cr];"
            f"[cr]fade=in:st=0.1:d=0.45:alpha=1[cf];"
            f"[bg][cf]overlay=x=(W-w)/2:y='{slide_y}'[ov];"

            # flash intro word (first 0.55s)
            f"[ov]drawtext={_ff}text='{word}':"
            f"fontsize=48:fontcolor=white:"
            f"alpha='max(0,min(1,t*6)*min(1,(0.55-t)*8))':"
            f"x=(w-text_w)/2:y=H*0.04:"
            f"shadowcolor={a}@0.9:shadowx=3:shadowy=3[fw];"

            # rarity
            f"[fw]drawtext={_ff}text='{rar}':"
            f"fontsize=22:fontcolor={a}:"
            f"alpha='min(1,max(0,(t-0.6)*4))':"
            f"x=(w-text_w)/2:y=H*0.820:"
            f"shadowcolor=black:shadowx=1:shadowy=1[r1];"

            # card name
            f"[r1]drawtext={_ff}text='{name}':"
            f"fontsize=36:fontcolor=white:"
            f"alpha='min(1,max(0,(t-0.75)*4))':"
            f"x=(w-text_w)/2:y=H*0.873:"
            f"shadowcolor=black:shadowx=2:shadowy=2[en];"

            # price
            f"[en]drawtext={_ff}text='{price}':"
            f"fontsize=52:fontcolor={a}:"
            f"alpha='min(1,max(0,(t-0.9)*4))':"
            f"x=(w-text_w)/2:y=H*0.922:"
            f"shadowcolor=black@0.95:shadowx=3:shadowy=3[pr];"

            # branding
            f"[pr]drawtext={_ff}text='TCG Nakama':"
            f"fontsize=20:fontcolor=white@0.55:"
            f"alpha='min(1,max(0,(t-1.05)*4))':"
            f"x=(w-text_w)/2:y=H*0.962:"
            f"shadowcolor=black:shadowx=1:shadowy=1"
        )
        cmd = [
            "ffmpeg","-y",
            "-stream_loop","-1","-i", bg_path,
            "-i", img_path,
            "-filter_complex", fc,
            "-t", str(CARD_SEC),
            "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p","-an", seg
        ]

    elif has_img:
        # ── FALLBACK: gradient bg + static card (no Pollo video) ──
        slide_y = "if(lt(t\\,0.55)\\,(H-h)/2-80+(H+200)*(1-t/0.45)\\,(H-h)/2-80)"
        fc = (
            f"[0:v]fade=in:st=0:d=0.4[bg];"
            f"[1:v]scale={CARD_W}:-1,format=rgba[cr];"
            f"[cr]fade=in:st=0.1:d=0.45:alpha=1[cf];"
            f"[bg][cf]overlay=x=(W-w)/2:y='{slide_y}'[ov];"
            f"[ov]drawtext={_ff}text='{rar}':"
            f"fontsize=22:fontcolor={a}:"
            f"alpha='min(1,max(0,(t-0.65)*4))':"
            f"x=(w-text_w)/2:y=H*0.820:"
            f"shadowcolor=black:shadowx=1:shadowy=1[r1];"
            f"[r1]drawtext={_ff}text='{name}':"
            f"fontsize=36:fontcolor=white:"
            f"alpha='min(1,max(0,(t-0.8)*4))':"
            f"x=(w-text_w)/2:y=H*0.873:"
            f"shadowcolor=black:shadowx=2:shadowy=2[en];"
            f"[en]drawtext={_ff}text='{price}':"
            f"fontsize=52:fontcolor={a}:"
            f"alpha='min(1,max(0,(t-0.95)*4))':"
            f"x=(w-text_w)/2:y=H*0.922:"
            f"shadowcolor=black@0.95:shadowx=3:shadowy=3[pr];"
            f"[pr]drawtext={_ff}text='TCG Nakama':"
            f"fontsize=20:fontcolor=white@0.55:"
            f"alpha='min(1,max(0,(t-1.1)*4))':"
            f"x=(w-text_w)/2:y=H*0.962:"
            f"shadowcolor=black:shadowx=1:shadowy=1"
        )
        cmd = [
            "ffmpeg","-y",
            "-stream_loop","-1","-i", bg_path,
            "-i", img_path,
            "-filter_complex", fc,
            "-t", str(CARD_SEC),
            "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p","-an", seg
        ]

    else:
        # ── MINIMAL: bg only + text ──
        vf = (
            f"drawtext={_ff}text='{name}':fontsize=36:fontcolor=white:"
            f"alpha='min(1,max(0,(t-0.5)*4))':"
            f"x=(w-text_w)/2:y=H*0.45:shadowcolor=black:shadowx=2:shadowy=2,"
            f"drawtext={_ff}text='{price}':fontsize=52:fontcolor={a}:"
            f"alpha='min(1,max(0,(t-0.7)*4))':"
            f"x=(w-text_w)/2:y=H*0.53:shadowcolor=black:shadowx=3:shadowy=3"
        )
        cmd = [
            "ffmpeg","-y","-stream_loop","-1","-i", bg_path,
            "-vf", vf, "-t", str(CARD_SEC),
            "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p","-an", seg
        ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Segment {idx} failed:\n{r.stderr}")
    return seg


# ── xfade video-only concat ──────────────────────────────
def concat_xfade(seg_paths: list, seg_durations: list, out_path: str):
    n = len(seg_paths)
    if n == 1:
        import shutil; shutil.copy(seg_paths[0], out_path); return

    inputs = []
    for p in seg_paths: inputs += ["-i", p]

    # Normalise all inputs to 30fps, then xfade
    # fps= fixes frame-rate mismatches between intro clips and Sora-2 outputs
    fps_parts = [f"[{i}:v]fps=30[v{i}]" for i in range(n)]
    v_parts, prev, cumul = [], "[v0]", 0.0
    for i in range(1, n):
        cumul  += seg_durations[i-1]
        offset  = cumul - XFADE_SEC * i
        lbl     = f"[xv{i}]" if i < n-1 else "[outv]"
        v_parts.append(f"{prev}[v{i}]xfade=transition=fade:offset={offset:.2f}:duration={XFADE_SEC}{lbl}")
        prev = f"[xv{i}]"

    fc = ";".join(fps_parts + v_parts)

    r = subprocess.run([
        "ffmpeg","-y", *inputs,
        "-filter_complex", fc,
        "-map","[outv]","-an",
        "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p", out_path
    ], capture_output=True, text=True)

    if r.returncode != 0 or not os.path.exists(out_path):
        print(f"  [WARN] xfade failed ({r.stderr[-80:]}), using simple concat")
        lst = f"{OUTPUT_DIR}/concat.txt"
        with open(lst,'w') as f:
            for p in seg_paths: f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,
                        "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p","-an",
                        out_path], capture_output=True)

    if not os.path.exists(out_path):
        raise RuntimeError(f"Concat failed: {out_path}")

    mb    = os.path.getsize(out_path) / 1024 / 1024
    total = sum(seg_durations) - (n-1) * XFADE_SEC
    print(f"  -> {out_path} ({mb:.1f} MB, ~{total:.0f}s)")


# ── Main ─────────────────────────────────────────────────
async def main():
    ensure_ffmpeg()  # install static binary on Linux if needed

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("=" * 62)
    print(f"TCG NAKAMA — NEW CARDS SHOWCASE  [{ts}]")
    print("=" * 62)

    gcs = get_gcs()

    # 1. Fetch cards
    print(f"\n[SHOPIFY] Fetching top {CARD_LIMIT} cards...")
    cards = await get_fresh_pulls()
    for i, c in enumerate(cards):
        print(f"  {i+1}. {eng(c['title']):26s} | {c.get('rarity',''):14s} | JPY {c['price']:,.0f}")

    # 2. Download images
    print(f"\n[IMAGES] Downloading card images...")
    img_paths = []
    img_urls  = []
    for c in cards:
        url  = c.get('image','')
        path = f"{OUTPUT_DIR}/{c['id'].split('/')[-1]}_card.png"
        if url:
            try: urllib.request.urlretrieve(url, path); img_paths.append(path); img_urls.append(url)
            except: img_paths.append(None); img_urls.append('')
        else:
            img_paths.append(None); img_urls.append('')
        print(f"  {'OK' if img_paths[-1] else 'MISS'}: {path.split('/')[-1]}")

    # 3. Per-card: Gemini analysis + Sora-2 background (sequential)
    print(f"\n[PIPELINE] Per-card AI analysis + Pollo-1.6 background...")
    analyses = []
    bg_paths = []

    for i, card in enumerate(cards):
        print(f"\n  [{i+1}/{len(cards)}] {eng(card['title'])}")

        # Gemini analysis
        print(f"    [Gemini] Analyzing...")
        if img_paths[i]:
            analysis = analyze_card(img_paths[i], card['title'], i)
        else:
            analysis = {"name": eng(card['title']), "type": "Normal",
                        "motion": "subtle shimmer emanates from the character, particles drift from its form",
                        "accent_color": "#60A0FF", "intro_word": "REVEALED"}
        analyses.append(analysis)
        card_name = analysis.get('name', eng(card['title']))
        motion    = analysis.get('motion', 'subtle shimmer emanates from the character')
        print(f"    [Gemini] {card_name} ({analysis['type']}) — '{analysis['intro_word']}'")
        print(f"    [Motion] {motion[:90]}")

        # Pollo-1.6 background
        bg = f"{OUTPUT_DIR}/bg_{i:02d}.mp4"
        print(f"    [Pollo-1.6] Generating background", end=" ")
        try:
            generate_bg(img_urls[i], card_name, motion, bg)
            mb = os.path.getsize(bg) / 1024 / 1024
            print(f"    [OK] {mb:.1f} MB")
        except Exception as e:
            print(f"\n    [WARN] {e} — gradient fallback")
            gradient_bg(analysis.get('accent_color','#3060FF'), bg)
        bg_paths.append(bg)

    # 4. Build blurry-card intro from first card image
    print(f"\n[FFMPEG] Building intro (blurry first card)...")
    intro_seg = make_intro(img_paths[0] if img_paths else None)
    print(f"  [OK] Intro done ({INTRO_SEC}s)")

    # 5. Build per-card segments
    print(f"\n[FFMPEG] Building {len(cards)} card segments...")
    seg_paths = [intro_seg]
    seg_durs  = [float(INTRO_SEC)]
    for i, (card, analysis, bg, img) in enumerate(zip(cards, analyses, bg_paths, img_paths)):
        print(f"  [{i+1}/{len(cards)}] {analysis['name']} ({analysis['type']})")
        seg = make_card_segment(bg, img, card, analysis, i)
        seg_paths.append(seg)
        seg_durs.append(float(CARD_SEC))
        print(f"    -> {seg}")

    # 6. xfade concat (video-only, no audio)
    final = f"{OUTPUT_DIR}/new_cards_{ts}.mp4"
    print(f"\n[FFMPEG] Concatenating with crossfade...")
    concat_xfade(seg_paths, seg_durs, final)

    # 7. Upload
    print(f"\n[GCS] Uploading...")
    video_uri, video_public_url = gcs_upload(gcs, final, f"showcase/new_cards_{ts}.mp4")

    # Record which card IDs were used so the scheduler can deduplicate next run
    used_ids = [c['id'] for c in cards]
    last_run = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "card_ids": used_ids,
    }
    last_run_path = f"{OUTPUT_DIR}/last_run.json"
    with open(last_run_path, 'w', encoding='utf-8') as f:
        json.dump(last_run, f, ensure_ascii=False, indent=2)
    gcs_upload(gcs, last_run_path, "showcase/last_run.json")

    manifest  = {
        "file": f"new_cards_{ts}.mp4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cards": [{
            "title":  c['title'], "name":  a.get('name'),
            "type":   a.get('type'), "word":  a.get('intro_word'),
            "price":  c['price'],
        } for c, a in zip(cards, analyses)],
        "gcs_video_uri": video_uri,
        "public_url": video_public_url,
        "status": "pending_qa",
    }
    mpath = f"{OUTPUT_DIR}/manifest_{ts}.json"
    with open(mpath,'w',encoding='utf-8') as f: json.dump(manifest,f,ensure_ascii=False,indent=2)
    gcs_upload(gcs, mpath, f"showcase/manifest_{ts}.json")

    print(f"\n{'='*62}")
    print(f"DONE!  {len(cards)}-card showcase | intro: blurry card → reveal")
    print(f"  Local : {os.path.abspath(final)}")
    print(f"  GCS   : {video_uri}")
    print(f"  URL   : {video_public_url}")
    print(f"{'='*62}")

    # 8. Notify Zapier
    print(f"\n[ZAPIER] Firing webhook...")
    notify_zapier(manifest)


    if os.name == 'nt':  # Windows only
        subprocess.Popen(["explorer", "/select,", os.path.abspath(final)])

if __name__ == "__main__":
    asyncio.run(main())
