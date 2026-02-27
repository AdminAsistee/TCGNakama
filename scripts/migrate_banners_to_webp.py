"""
One-time migration script: converts existing banner images in app/static/banners/
from PNG/JPG to WebP, then updates the database paths accordingly.

Usage:
    cd C:\\Users\\amrca\\Documents\\antigravity\\tcgnakama
    python scripts/migrate_banners_to_webp.py

Run this ONCE after deploying the WebP changes.
"""
import sys
import os
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.utils.image_utils import convert_to_webp

# -- Database setup --
from app.database import SessionLocal
from app.models import Banner

BANNER_DIR = PROJECT_ROOT / "app" / "static" / "banners"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png"}


def migrate():
    converted = 0
    skipped = 0
    errors = 0

    db = SessionLocal()
    try:
        for src_path in sorted(BANNER_DIR.iterdir()):
            if src_path.suffix.lower() not in SUPPORTED_EXTS:
                continue

            dest_path = src_path.with_suffix(".webp")

            # Convert the file
            try:
                image_data = src_path.read_bytes()
                webp_data = convert_to_webp(image_data, quality=85, max_width=1920)
                dest_path.write_bytes(webp_data)
                print(f"  ✓ Converted: {src_path.name} → {dest_path.name}")
            except Exception as e:
                print(f"  ✗ Error converting {src_path.name}: {e}")
                errors += 1
                continue

            # Update database: find banners referencing the old path
            old_static_paths = [
                f"/static/banners/{src_path.name}",
                f"static/banners/{src_path.name}",
                src_path.name,
            ]
            new_static_path = f"/static/banners/{dest_path.name}"

            db_updated = False
            for banner in db.query(Banner).all():
                if banner.image_path and any(
                    banner.image_path.endswith(p) for p in [src_path.name]
                ):
                    old = banner.image_path
                    banner.image_path = new_static_path
                    print(f"    DB updated: '{old}' → '{new_static_path}'")
                    db_updated = True

            db.commit()

            # Delete old file only if conversion succeeded
            try:
                src_path.unlink()
                print(f"    Deleted original: {src_path.name}")
            except Exception as e:
                print(f"    Warning: could not delete {src_path.name}: {e}")

            converted += 1

        print(f"\nMigration complete: {converted} converted, {skipped} skipped, {errors} errors.")

    finally:
        db.close()


if __name__ == "__main__":
    print(f"Scanning: {BANNER_DIR}\n")
    if not BANNER_DIR.exists():
        print("Banner directory not found. Nothing to do.")
        sys.exit(0)
    migrate()
