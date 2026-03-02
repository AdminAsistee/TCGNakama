import psycopg2

# Connect to the production database
conn_params = {
    'host': 'app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com',
    'port': 25060,
    'user': 'db',
    'password': 'AVNS_ZHMCwgpxwgIOeLPK5gt',
    'database': 'db',
    'sslmode': 'require'
}

try:
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    print("Current banner image paths in production database:")
    print("=" * 80)
    cursor.execute("SELECT id, title, image_path FROM banners ORDER BY display_order")
    banners = cursor.fetchall()
    
    for b in banners:
        print(f"ID {b[0]}: {b[1]}")
        print(f"  Image Path: '{b[2]}'")
        print(f"  Starts with /static/: {b[2].startswith('/static/') if b[2] else 'N/A'}")
        print(f"  Starts with http: {b[2].startswith(('http://', 'https://')) if b[2] else 'N/A'}")
        print()
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
