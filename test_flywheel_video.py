"""
Flywheel Video — Animated Fresh Pulls Showcase Reel
- Type-aware background + flash animation per card
- Card slides up from bottom with fade-in
- xfade crossfade transitions between cards
- Saves to GCS
"""
import io, sys, os, time, asyncio, json, subprocess, urllib.request, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)
from datetime import datetime, timezone

OUTPUT_DIR  = "flywheel_test_output/videos"
GCS_BUCKET  = os.getenv("GCS_BUCKET", "ready-bucket")
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "tcgnakama")
VEO_LOC     = "us-central1"
CARD_LIMIT  = 6
HOLD_SEC    = 4       # seconds card is shown fully
FADE_SEC    = 0.5     # fade-in duration for card
XFADE_SEC  = 0.4     # crossfade between cards
SEGMENT_SEC = HOLD_SEC + FADE_SEC   # total per card = 4.5s
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Type detection ────────────────────────────────────────────────────────────
# Maps keywords in card name/tags → (type_name, flash_color_hex, veo_mood)
TYPE_MAP = [
    (["pikachu","raichu","jolteon","zapdos","thundurus","enel","eneru",
      "chien-pao","zeraora","luxray","magnezone","electrode"],
     "lightning", "FFE000",
     "electric yellow lightning bolts crackling, bright electrical discharge energy"),

    (["charizard","arcanine","blaziken","infernape","heatran","reshiram",
      "cinderace","armarouge","moltres"],
     "fire", "FF4500",
     "intense fire flames bursting upward, deep orange and red ember glow"),

    (["blastoise","vaporeon","gyarados","suicune","kyogre","palkia",
      "primarina","palafin","wishiwashi","milotic"],
     "water", "00BFFF",
     "flowing ocean waves, deep blue water caustics, bioluminescent particles"),

    (["mewtwo","gardevoir","alakazam","espeon","lunala","mew",
      "gallade","hatterene","slowbro"],
     "psychic", "E040FB",
     "swirling purple psychic energy, galaxy vortex, ethereal pink wisps"),

    (["gengar","mismagius","chandelure","dragapult","mimikyu",
      "spiritomb","giratina","zoroark"],
     "ghost", "7B1FA2",
     "dark purple ghostly shadows, haunting fog, spectral floating orbs"),

    (["rayquaza","dragonite","salamence","garchomp","dragonair",
      "kommo-o","haxorus","kingdra","noivern"],
     "dragon", "304FFE",
     "dragon scales shimmer, iridescent blue-gold energy vortex swirl"),

    (["lucario","machamp","conkeldurr","hawlucha","urshifu","hitmonlee"],
     "fighting", "FF6D00",
     "explosive shockwave rings, ember sparks, intense battle aura energy"),

    (["venusaur","sceptile","leafeon","shaymin","virizion","rowlet",
      "decidueye","lilligant","gossifleur","houndstone"],
     "grass", "00C853",
     "lush green leaves swirling, nature energy vines glowing, forest light rays"),
]

DEFAULT_MOOD = "deep navy holographic rainbow shimmer, prismatic light refractions, luxury TCG foil effect"
DEFAULT_FLASH = "60A0FF"

def detect_type(card: dict):
    name = (card.get('title') or '').lower()
    tags = [t.lower() for t in (card.get('tags') or [])]
    combined = name + ' ' + ' '.join(tags)
    for keywords, type_name, flash_hex, mood in TYPE_MAP:
        if any(kw in combined for kw in keywords):
            return type_name, flash_hex, mood
    rarity = (card.get('rarity') or '').lower()
    if 'secret' in rarity:
        return 'secret', 'FFD700', "golden holographic shimmer, rainbow prismatic foil, prestige collector glow"
    if 'ultra' in rarity:
        return 'ultra', 'E040FB', "deep purple cosmic starfield, glowing nebula energy, premium rainbow foil"
    return 'default', DEFAULT_FLASH, DEFAULT_MOOD


# ── GCS ──────────────────────────────────────────────────────────────────────
def get_gcs_client():
    from google.cloud import storage
    client = storage.Client(project=GCP_PROJECT)
    try: client.get_bucket(GCS_BUCKET)
    except: client.create_bucket(GCS_BUCKET, location="US")
    return client

def gcs_upload(client, local, remote):
    client.bucket(GCS_BUCKET).blob(remote).upload_from_filename(local)
    print(f"  [GCS] gs://{GCS_BUCKET}/{remote}")
    return f"gs://{GCS_BUCKET}/{remote}"


# ── Shopify ───────────────────────────────────────────────────────────────────
async def get_fresh_pulls():
    from app.dependencies import ShopifyClient
    client = ShopifyClient()
    products = await client.get_products()
    in_stock = [p for p in products if p.get('totalInventory', 0) > 0]
    return sorted(in_stock, key=lambda x: x.get('createdAt', ''), reverse=True)[:CARD_LIMIT]


# ── Veo background ────────────────────────────────────────────────────────────
def generate_veo_background(mood: str, type_name: str) -> str | None:
    from google import genai
    from google.genai import types
    bg_path = f"{OUTPUT_DIR}/bg_{type_name}.mp4"
    if os.path.exists(bg_path):
        print(f"  [VEO] Reusing {type_name} background")
        return bg_path

    prompt = (
        f"Cinematic animated background for TCG trading card video. "
        f"{mood}. "
        f"No cards, no text, no characters. 9:16 vertical format. "
        f"Smooth looping motion, premium feel."
    )
    client = genai.Client(vertexai=True, project=GCP_PROJECT, location=VEO_LOC)
    print(f"  [VEO] Generating {type_name} background...")
    try:
        op = client.models.generate_videos(
            model="veo-2.0-generate-001", prompt=prompt,
            config=types.GenerateVideosConfig(aspect_ratio="9:16", duration_seconds=5, number_of_videos=1),
        )
        elapsed = 0
        while not op.done and elapsed < 180:
            print(f"  [VEO] Waiting... ({elapsed}s)", end='\r')
            time.sleep(10); elapsed += 10
            op = client.operations.get(op)
        if not op.done: return None
        video = op.response.generated_videos[0].video
        if hasattr(video, 'video_bytes') and video.video_bytes:
            with open(bg_path, 'wb') as f: f.write(video.video_bytes)
        elif hasattr(video, 'uri') and video.uri:
            from google.cloud import storage as gcs
            c = gcs.Client(project=GCP_PROJECT)
            bkt, blob = video.uri.replace("gs://","").split("/",1)
            c.bucket(bkt).blob(blob).download_to_filename(bg_path)
        else: return None
        print(f"\n  [VEO] Saved -> {bg_path}")
        return bg_path
    except Exception as e:
        print(f"\n  [VEO] Error: {e}")
        return None

def gradient_bg(type_name: str, flash_hex: str) -> str:
    bg_path = f"{OUTPUT_DIR}/bg_{type_name}.mp4"
    r = int(flash_hex[0:2],16); g = int(flash_hex[2:4],16); b = int(flash_hex[4:6],16)
    dr,dg,db = max(5,r//8), max(5,g//8), max(5,b//8)
    cmd = [
        "ffmpeg","-y","-f","lavfi",
        "-i",f"color=c=0x0a0a14:size=720x1280:rate=30",
        "-vf", f"geq=r='clip({dr}+Y/30,0,{min(r,120)})':g='clip({dg}+Y/35,0,{min(g,120)})':b='clip({db}+Y/20,0,{min(b,150)})',boxblur=20:1",
        "-t","5","-c:v","libx264","-pix_fmt","yuv420p", bg_path
    ]
    subprocess.run(cmd, capture_output=True)
    return bg_path


# ── Flash overlay (type intro flash) ─────────────────────────────────────────
def make_flash(flash_hex: str, duration: float = 0.5) -> str:
    flash_path = f"{OUTPUT_DIR}/flash_{flash_hex}.mp4"
    if os.path.exists(flash_path): return flash_path
    # Bright colored burst that fades out quickly
    cmd = [
        "ffmpeg","-y","-f","lavfi",
        "-i",f"color=c=0x{flash_hex}:size=720x1280:rate=30",
        "-vf",f"fade=out:st=0.1:d={duration-0.1}",
        "-t",str(duration),"-c:v","libx264","-pix_fmt","yuv420p", flash_path
    ]
    subprocess.run(cmd, capture_output=True)
    return flash_path


# ── Card slide-up + fade-in segment ──────────────────────────────────────────
def safe(s): return re.sub(r"['\:\\#@\[\]{}()]", "", s)
def english_name(title):
    m = re.search(r'\(([^)]+)\)', title)
    return m.group(1)[:24] if m else title.split(' - ')[0][:24]
def rarity_accent(rarity):
    r = (rarity or '').lower()
    if 'secret' in r: return "0xFFD700"
    if 'ultra'  in r: return "0xE040FB"
    if 'rare'   in r: return "0x40C4FF"
    return "0xFFFFFF"

def make_card_segment(bg_path: str, card_img: str | None,
                      flash_hex: str, card: dict, idx: int) -> str:
    seg_path = f"{OUTPUT_DIR}/seg_{idx:02d}.mp4"
    eng      = safe(english_name(card['title']))
    set_info = safe(card['title'].split(' - ')[-1]) if ' - ' in card['title'] else ''
    price    = f"JPY {card['price']:,.0f}"
    accent   = rarity_accent(card.get('rarity'))

    # Card width = 50% of 720px bg = 360px (not too big)
    card_w = 360

    # Flash overlay on bg: blend flash on top for 0.5s, then normal bg
    # Card slides up: starts at y=H (off-screen), lands at y=(H-h)/2-60
    # Uses overlay y='(H-h)/2-60 + max(0, H*(1-2*(t-0.3)))'  (slide up during t=0.3-0.8)
    # Card fade-in: fade starts at t=0.3, done by t=0.7

    flash_path = make_flash(flash_hex)

    if card_img:
        # Pre-compute to avoid backslash-in-f-string (Python 3.11)
        rarity_text = safe(card.get('rarity') or 'IN STOCK').upper()
        slide_y = "(H-h)/2-50 + max(0,(H+100)*max(0,1-(t-0.3)/0.5))"
        filter_complex = (
            # Step1: layer flash over bg (flash is 0.5s, then transparent)
            f"[0:v][2:v]overlay=0:0:enable='lt(t,0.5)'[bg_flash];"

            # Step2: scale card to target width
            f"[1:v]scale={card_w}:-1,format=rgba[card_raw];"

            # Step3: animated fade-in on card (starts at t=0.3)
            f"[card_raw]fade=in:st=0.3:d=0.4:alpha=1[card_fade];"

            # Step4: slide card up from below into center
            f"[bg_flash][card_fade]overlay="
            f"x=(W-w)/2:"
            f"y='{slide_y}'[ov];"

            # Step5: text overlays (visible after card is up)
            f"[ov]drawtext=text='{rarity_text}':"
            f"fontsize=24:fontcolor={accent}:alpha='min(1,max(0,(t-0.8)*3))':"
            f"x=(w-text_w)/2:y=H*0.762:shadowcolor=black:shadowx=1:shadowy=1[r1];"

            f"[r1]drawtext=text='{eng}':"
            f"fontsize=38:fontcolor=white:alpha='min(1,max(0,(t-0.9)*3))':"
            f"x=(w-text_w)/2:y=H*0.828:shadowcolor=black:shadowx=2:shadowy=2[en];"

            f"[en]drawtext=text='{price}':"
            f"fontsize=54:fontcolor={accent}:alpha='min(1,max(0,(t-1.0)*3))':"
            f"x=(w-text_w)/2:y=H*0.886:shadowcolor=black@0.95:shadowx=3:shadowy=3[pr];"

            f"[pr]drawtext=text='TCG Nakama':"
            f"fontsize=24:fontcolor=white@0.55:alpha='min(1,max(0,(t-1.1)*3))':"
            f"x=(w-text_w)/2:y=H*0.942:shadowcolor=black:shadowx=1:shadowy=1"
        )
        cmd = [
            "ffmpeg","-y",
            "-stream_loop","-1","-i", bg_path,
            "-i", card_img,
            "-stream_loop","-1","-i", flash_path,
            "-filter_complex", filter_complex,
            "-t", str(SEGMENT_SEC),
            "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p",
            seg_path
        ]
    else:
        # No card image — just bg + flash + text
        vf = (
            f"drawtext=text='{eng}':fontsize=38:fontcolor={accent}:"
            f"x=(w-text_w)/2:y=H*0.45:shadowcolor=black:shadowx=2:shadowy=2,"
            f"drawtext=text='{price}':fontsize=54:fontcolor=white:"
            f"x=(w-text_w)/2:y=H*0.52:shadowcolor=black:shadowx=3:shadowy=3"
        )
        cmd = [
            "ffmpeg","-y",
            "-stream_loop","-1","-i", bg_path,
            "-vf", vf,
            "-t", str(SEGMENT_SEC),
            "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p",
            seg_path
        ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Segment {idx}:\n{r.stderr[-500:]}")
    return seg_path


# ── xfade concat ─────────────────────────────────────────────────────────────
def xfade_concat(seg_paths: list, out_path: str) -> str:
    """Chain segments with crossfade transitions."""
    if len(seg_paths) == 1:
        import shutil; shutil.copy(seg_paths[0], out_path)
        return out_path

    # Build a complex xfade chain
    n = len(seg_paths)
    inputs = []
    for p in seg_paths:
        inputs += ["-i", p]

    seg_dur = SEGMENT_SEC
    # Filter: [0][1]xfade=offset=<end-xfade>:duration=<xfade>[x01]; [x01][2]xfade=...
    filter_parts = []
    prev_label = "[0:v]"
    for i in range(1, n):
        offset = seg_dur * i - XFADE_SEC * i
        out_label = f"[x{i}]" if i < n-1 else ""
        filter_parts.append(
            f"{prev_label}[{i}:v]xfade=transition=fade:offset={offset:.2f}:duration={XFADE_SEC}{out_label}"
        )
        prev_label = f"[x{i}]"

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg","-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p",
        out_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [WARN] xfade failed, using simple concat: {r.stderr[-200:]}")
        # Fallback simple concat
        list_file = f"{OUTPUT_DIR}/concat_list.txt"
        with open(list_file,'w') as f:
            for p in seg_paths: f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,"-c","copy",out_path], capture_output=True)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    total_s = n * SEGMENT_SEC - (n-1) * XFADE_SEC
    print(f"  [FFMPEG] Showcase reel -> {out_path} ({size_mb:.1f} MB, ~{total_s:.0f}s)")
    return out_path


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    print("=" * 62)
    print("FLYWHEEL — ANIMATED FRESH PULLS SHOWCASE REEL")
    print("=" * 62)

    gcs_client = get_gcs_client()

    print(f"\n[SHOPIFY] Fetching top {CARD_LIMIT} Fresh Pulls...")
    cards = await get_fresh_pulls()
    print(f"  {len(cards)} cards:")
    for i, c in enumerate(cards, 1):
        type_name, _, _ = detect_type(c)
        print(f"  {i}. {english_name(c['title']):26s} | {c.get('rarity'):14s} | {type_name:10s} | JPY {c['price']:,.0f}")

    # Generate per-type Veo backgrounds (cached if same type repeats)
    print(f"\n[VEO] Generating type-specific backgrounds...")
    bg_cache = {}
    for card in cards:
        type_name, flash_hex, mood = detect_type(card)
        if type_name not in bg_cache:
            bg = generate_veo_background(mood, type_name)
            bg_cache[type_name] = bg if bg else gradient_bg(type_name, flash_hex)

    # Build segments
    print(f"\n[FFMPEG] Building {len(cards)} animated segments...")
    seg_paths = []
    for i, card in enumerate(cards):
        type_name, flash_hex, _ = detect_type(card)
        eng = english_name(card['title'])
        print(f"  [{i+1}/{len(cards)}] {eng} ({type_name})")
        bg = bg_cache[type_name]
        card_id  = card['id'].split('/')[-1]
        img_path = f"{OUTPUT_DIR}/{card_id}_card.png"
        has_img  = False
        if card.get('image'):
            try: urllib.request.urlretrieve(card['image'], img_path); has_img=True
            except: pass
        seg = make_card_segment(bg, img_path if has_img else None, flash_hex, card, i)
        seg_paths.append(seg)
        print(f"       -> {seg}")

    # Crossfade concat
    print(f"\n[FFMPEG] Concatenating with crossfade transitions...")
    final_path = f"{OUTPUT_DIR}/fresh_pulls_showcase.mp4"
    xfade_concat(seg_paths, final_path)

    # Upload
    print(f"\n[GCS] Uploading...")
    video_uri = gcs_upload(gcs_client, final_path, "showcase/fresh_pulls_showcase.mp4")
    manifest = {
        "title": "Fresh Pulls Showcase",
        "cards": [{"title": c['title'], "price_jpy": c['price'], "type": detect_type(c)[0]} for c in cards],
        "status": "pending_qa",
        "gcs_video_uri": video_uri,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    mpath = f"{OUTPUT_DIR}/fresh_pulls_manifest.json"
    with open(mpath,'w',encoding='utf-8') as f: json.dump(manifest,f,ensure_ascii=False,indent=2)
    gcs_upload(gcs_client, mpath, "showcase/manifest.json")

    print(f"\n{'='*62}")
    print(f"DONE! {len(cards)}-card animated showcase reel")
    print(f"  Local : {os.path.abspath(final_path)}")
    print(f"  GCS   : {video_uri}")
    print(f"{'='*62}")

    subprocess.Popen(["explorer", "/select,", os.path.abspath(final_path)])

if __name__ == "__main__":
    asyncio.run(main())
