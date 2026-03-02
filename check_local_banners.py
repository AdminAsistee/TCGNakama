import sqlite3

try:
    # Connect to local SQLite database
    conn = sqlite3.connect('app/data/costs.db')
    cursor = conn.cursor()
    
    # Check if banners table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='banners'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print("[INFO] Banners table found in local database\n")
        
        # Query banners
        cursor.execute("SELECT id, title, subtitle, image_path, gradient, is_active, display_order FROM banners ORDER BY display_order")
        banners = cursor.fetchall()
        
        print(f"[SUCCESS] Found {len(banners)} banners:\n")
        print("=" * 100)
        
        for banner in banners:
            banner_id, title, subtitle, image_path, gradient, is_active, display_order = banner
            print(f"ID: {banner_id}")
            print(f"Title: {title}")
            print(f"Subtitle: {subtitle}")
            print(f"Image Path: '{image_path}' (NULL: {image_path is None})")
            print(f"Gradient: {gradient}")
            print(f"Active: {is_active}")
            print(f"Display Order: {display_order}")
            print("=" * 100)
    else:
        print("[INFO] Banners table does not exist in local database")
        print("[INFO] This is expected - banners are likely only in production PostgreSQL")
    
    conn.close()
    
except Exception as e:
    print(f"[ERROR] Failed to query local database: {e}")
