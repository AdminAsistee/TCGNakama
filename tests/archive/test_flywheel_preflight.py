"""
Flywheel Pre-flight: GCP connection test
Run: python test_flywheel_preflight.py
"""
import os
import sys

# Fix Windows cp932 encoding for Unicode output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(override=True)

print("=" * 50)
print("FLYWHEEL PRE-FLIGHT CHECK")
print("=" * 50)

# 1. Check env vars
project_id = os.getenv("GCP_PROJECT_ID")
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

print(f"\n[ENV] GCP_PROJECT_ID       : {project_id or 'NOT SET ❌'}")
print(f"[ENV] GOOGLE_CREDENTIALS   : {creds_path or 'NOT SET ❌'}")
print(f"[ENV] FB_PAGE_ID           : {'SET ✅' if os.getenv('FB_PAGE_ID') else 'not set (will skip)'}")
print(f"[ENV] IG_USER_ID           : {'SET ✅' if os.getenv('IG_USER_ID') else 'not set (will skip)'}")
print(f"[ENV] YOUTUBE_TOKEN        : {'SET ✅' if os.getenv('YOUTUBE_TOKEN') else 'not set (will skip)'}")

if creds_path and not os.path.exists(creds_path):
    print(f"\n[ERROR] Credentials file not found at: {creds_path}")
    sys.exit(1)

# 2. Test GCS connection
print("\n[TEST] Connecting to Google Cloud Storage...")
try:
    from google.cloud import storage
    client = storage.Client(project=project_id)
    print(f"[OK] Connected to GCS — Project: {client.project} ✅")

    # Try to access or create the ready-bucket
    bucket_name = os.getenv("GCS_BUCKET", "ready-bucket")
    try:
        bucket = client.get_bucket(bucket_name)
        print(f"[OK] Bucket '{bucket_name}' found ✅")
    except Exception:
        print(f"[INFO] Bucket '{bucket_name}' not found — will be created on first Producer run")
except ImportError:
    print("[ERROR] google-cloud-storage not installed. Run: pip install google-cloud-storage")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] GCS connection failed: {e}")
    sys.exit(1)

# 3. Test Vertex AI / Gemini access
print("\n[TEST] Checking Vertex AI access...")
try:
    import google.auth
    creds, proj = google.auth.default()
    print(f"[OK] Google Auth default credentials loaded — Project: {proj} ✅")
except Exception as e:
    print(f"[WARN] Vertex AI auth check skipped: {e}")

# 4. Test app endpoint
print("\n[TEST] Checking app Fresh Pulls endpoint...")
try:
    import urllib.request
    with urllib.request.urlopen("http://localhost:8000/", timeout=5) as resp:
        status = resp.status
        body = resp.read(500).decode("utf-8", errors="ignore")
        has_fresh = "Fresh Pulls" in body or "fresh_pulls" in body
        print(f"[OK] App responded — HTTP {status} ✅")
        print(f"[OK] Fresh Pulls section {'found ✅' if has_fresh else 'NOT found in response ⚠️'}")
except Exception as e:
    print(f"[WARN] App not reachable at localhost:8000 — start it first with: python main.py")

print("\n" + "=" * 50)
print("Pre-flight complete. Ready to run /flywheel")
print("=" * 50)
