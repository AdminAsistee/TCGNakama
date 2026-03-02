import psycopg2

# Connect to the CORRECT database (db database that your app uses)
conn_params = {
    'host': 'app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com',
    'port': 25060,
    'user': 'db',
    'password': 'AVNS_ZHMCwgpxwgIOeLPK5gt',
    'database': 'db',
    'sslmode': 'require'
}

try:
    print("[INFO] Connecting to 'db' database (the one your app uses)...")
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    # Show current state
    print("\n[BEFORE] Current banners:")
    cursor.execute("SELECT id, title, image_path FROM banners ORDER BY display_order")
    banners = cursor.fetchall()
    for b in banners:
        img_display = b[2] if b[2] else 'NULL (gradient)'
        print(f"  ID {b[0]}: {b[1][:40]} | Image: {img_display}")
    
    # Fix: Set all image_path to NULL to use gradients
    print("\n[FIXING] Setting all banners to use gradients (image_path = NULL)...")
    cursor.execute("UPDATE banners SET image_path = NULL")
    conn.commit()
    
    # Show new state
    print("\n[AFTER] Updated banners:")
    cursor.execute("SELECT id, title, image_path FROM banners ORDER BY display_order")
    banners = cursor.fetchall()
    for b in banners:
        img_display = b[2] if b[2] else 'NULL (gradient)'
        print(f"  ID {b[0]}: {b[1][:40]} | Image: {img_display}")
    
    cursor.close()
    conn.close()
    print("\n[SUCCESS] Banners fixed! All image_path values set to NULL.")
    print("[INFO] Your live app should now display gradient backgrounds!")
    
except Exception as e:
    print(f"[ERROR] Failed: {e}")
