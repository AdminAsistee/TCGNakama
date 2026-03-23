import psycopg2

conn = psycopg2.connect(
    host="app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com",
    port=25060, database="defaultdb", user="doadmin",
    password="AVNS_WJtLYtseYwMSXA15Q5w", sslmode="require"
)
cur = conn.cursor()
cur.execute("SELECT id, is_published, slug FROM blog_posts;")
rows = cur.fetchall()
for r in rows:
    print(f"id={r[0]} is_published={r[1]} slug={r[2][:50] if r[2] else None}")

# Publish all unpublished posts
cur.execute("UPDATE blog_posts SET is_published = TRUE WHERE is_published = FALSE;")
conn.commit()
print(f"Published {cur.rowcount} posts.")
cur.close()
conn.close()
