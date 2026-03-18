"""
seed_banners.py - Auto-seeds default banners if the Banner table is empty.
Run manually: python seed_banners.py
Also called automatically at startup via app/main.py
"""
from app.database import SessionLocal
from app.models import Banner

DEFAULT_BANNERS = [
    {
        "title": "One Piece: Four Emperors",
        "subtitle": "The ultimate pirate cards have arrived",
        "cta_label": "Shop One Piece",
        "cta_link": "/",
        "image_path": None,
        "gradient": "from-red-900 via-orange-900 to-amber-900",
        "display_order": 1,
        "is_active": True,
    },
    {
        "title": "Pokémon Scarlet & Violet",
        "subtitle": "Explore the latest expansion — chase the illustrators",
        "cta_label": "Shop Pokémon",
        "cta_link": "/",
        "image_path": None,
        "gradient": "from-violet-900 via-purple-900 to-indigo-900",
        "display_order": 2,
        "is_active": True,
    },
    {
        "title": "One Piece: Romance Dawn",
        "subtitle": "Where the legend began — Romance Dawn collection",
        "cta_label": "Shop Romance Dawn",
        "cta_link": "/",
        "image_path": None,
        "gradient": "from-sky-900 via-cyan-900 to-teal-900",
        "display_order": 3,
        "is_active": True,
    },
]


def seed_banners():
    db = SessionLocal()
    try:
        count = db.query(Banner).count()
        if count == 0:
            print("🌱 Seeding default banners...")
            for data in DEFAULT_BANNERS:
                banner = Banner(**data)
                db.add(banner)
            db.commit()
            print(f"✅ Seeded {len(DEFAULT_BANNERS)} banners successfully.")
        else:
            print(f"ℹ️  Banners already exist ({count} found). Skipping seed.")
    except Exception as e:
        print(f"❌ Error seeding banners: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_banners()
