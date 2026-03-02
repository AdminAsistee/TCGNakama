import psycopg2
import os

# Connect to production database
conn_params = {
    'host': 'app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com',
    'port': 25060,
    'user': 'db',
    'password': 'AVNS_ZHMCwgpxwgIOeLPK5gt',
    'database': 'db',
    'sslmode': 'require'
}

# List local banner files
local_banners_dir = 'app/static/banners'
if os.path.exists(local_banners_dir):
    banner_files = sorted([f for f in os.listdir(local_banners_dir) if f.startswith('banner_') and f.endswith('.jpg')])
    print("Local banner files found:")
    for f in banner_files:
        print(f"  - {f}")
else:
    print("Banners directory not found locally")
    banner_files = []

try:
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    print("\nCurrent database banner paths:")
    cursor.execute("SELECT id, title, image_path FROM banners ORDER BY display_order")
    db_banners = cursor.fetchall()
    
    for b in db_banners:
        print(f"  ID {b[0]}: {b[1][:30]} -> {b[2]}")
    
    # Update paths to match local files
    if len(banner_files) >= len(db_banners):
        print(f"\nUpdating {len(db_banners)} banner paths...")
        for i, banner in enumerate(db_banners):
            banner_id = banner[0]
            new_path = f"/static/banners/{banner_files[i]}"
            cursor.execute("UPDATE banners SET image_path = %s WHERE id = %s", (new_path, banner_id))
            print(f"  ID {banner_id}: Updated to {new_path}")
        
        conn.commit()
        print("\n[SUCCESS] Banner paths updated!")
        
        # Verify
        print("\nVerifying updated paths:")
        cursor.execute("SELECT id, title, image_path FROM banners ORDER BY display_order")
        for b in cursor.fetchall():
            print(f"  ID {b[0]}: {b[1][:30]} -> {b[2]}")
    else:
        print(f"\n[WARNING] Not enough banner files ({len(banner_files)}) for {len(db_banners)} database entries")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
