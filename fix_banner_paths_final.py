import psycopg2

# Connect to production database
conn_params = {
    'host': 'app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com',
    'port': 25060,
    'user': 'db',
    'password': 'AVNS_ZHMCwgpxwgIOeLPK5gt',
    'database': 'db',
    'sslmode': 'require'
}

# Actual banner files that exist
banner_files = [
    'banner_1770714431.jpg',  # For banner ID 1
    'banner_1770714934.jpg',  # For banner ID 2
    'banner_1770715097.jpg',  # For banner ID 3
]

try:
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    print("Updating banner paths to match actual files...")
    print("=" * 80)
    
    for i, filename in enumerate(banner_files, start=1):
        new_path = f"/static/banners/{filename}"
        cursor.execute("UPDATE banners SET image_path = %s WHERE id = %s", (new_path, i))
        print(f"Banner ID {i}: {new_path}")
    
    conn.commit()
    
    # Verify
    print("\n" + "=" * 80)
    print("Verification - Updated banner paths:")
    cursor.execute("SELECT id, title, image_path FROM banners ORDER BY display_order LIMIT 3")
    for b in cursor.fetchall():
        title_safe = b[1].encode('ascii', 'ignore').decode('ascii')
        print(f"  ID {b[0]}: {title_safe[:30]} -> {b[2]}")
    
    cursor.close()
    conn.close()
    print("\n[SUCCESS] Banner paths updated!")
    
except Exception as e:
    print(f"Error: {e}")
