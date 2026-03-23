"""
Create blog_posts table directly on production PostgreSQL using SQLAlchemy
with the BlogPost model definition.
"""
import os
os.environ["DATABASE_URL"] = (
    "postgresql://doadmin:AVNS_WJtLYtseYwMSXA15Q5w@"
    "app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com"
    ":25060/defaultdb?sslmode=require"
)

from app.database import engine, Base
from app.models import BlogPost  # ensure model is registered

# Create only missing tables (safe to run multiple times)
Base.metadata.create_all(bind=engine)
print("Done. Tables now:")

import psycopg2
conn = psycopg2.connect(
    host="app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com",
    port=25060, database="defaultdb", user="doadmin",
    password="AVNS_WJtLYtseYwMSXA15Q5w", sslmode="require"
)
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
print([r[0] for r in cur.fetchall()])
cur.close()
conn.close()
