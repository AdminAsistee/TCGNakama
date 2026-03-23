import psycopg2

conn = psycopg2.connect(
    host="app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com",
    port=25060,
    database="defaultdb",
    user="doadmin",
    password="AVNS_WJtLYtseYwMSXA15Q5w",
    sslmode="require"
)
cur = conn.cursor()

# List all tables
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

# Check blog_posts specifically
if "blog_posts" in tables:
    cur.execute("SELECT COUNT(*) FROM blog_posts;")
    count = cur.fetchone()[0]
    print(f"blog_posts rows: {count}")
    if count > 0:
        cur.execute("SELECT id, title, is_published, published_at FROM blog_posts ORDER BY created_at DESC LIMIT 5;")
        for row in cur.fetchall():
            print(" ", row)
else:
    print("blog_posts table DOES NOT EXIST")

cur.close()
conn.close()
