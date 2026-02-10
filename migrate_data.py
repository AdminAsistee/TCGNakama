import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.cost_db import Base, ProductCost, ProductGrade, SearchLog

# Configuration
LOCAL_DB_PATH = "app/data/costs.db"
# This should be your DigitalOcean connection string
REMOTE_DB_URL = os.getenv("DATABASE_URL")

def migrate():
    if not REMOTE_DB_URL or "postgresql" not in REMOTE_DB_URL:
        print("Error: DATABASE_URL environment variable must be set to a PostgreSQL string.")
        print("Example: set DATABASE_URL=postgresql://user:pass@host:port/dbname")
        return

    if not os.path.exists(LOCAL_DB_PATH):
        print(f"Error: Local database not found at {LOCAL_DB_PATH}")
        return

    print(f"Starting migration: {LOCAL_DB_PATH} -> PostgreSQL")
    
    # Setup Remote Session
    remote_engine = create_engine(REMOTE_DB_URL)
    Base.metadata.create_all(bind=remote_engine)
    RemoteSession = sessionmaker(bind=remote_engine)
    remote_session = RemoteSession()

    # Setup Local Connection (raw sqlite for simplicity or SQLAlchemy)
    local_conn = sqlite3.connect(LOCAL_DB_PATH)
    local_cursor = local_conn.cursor()

    try:
        # 1. Migrate Costs
        print("Migrating Product Costs...")
        local_cursor.execute("SELECT product_id, buy_price FROM product_costs")
        for row in local_cursor.fetchall():
            cost = ProductCost(product_id=row[0], buy_price=row[1])
            remote_session.merge(cost) # merge handles upsert
        
        # 2. Migrate Grades
        print("Migrating Product Grades...")
        local_cursor.execute("SELECT product_id, grade FROM product_grades")
        for row in local_cursor.fetchall():
            grade = ProductGrade(product_id=row[0], grade=row[1])
            remote_session.merge(grade)

        # 3. Migrate Logs
        print("Migrating Search Logs...")
        local_cursor.execute("SELECT query, results_count, searched_at FROM search_logs")
        for row in local_cursor.fetchall():
            log = SearchLog(query=row[0], results_count=row[1], searched_at=row[2])
            remote_session.add(log)

        remote_session.commit()
        print("Success! Migration complete.")

    except Exception as e:
        print(f"Migration failed: {e}")
        remote_session.rollback()
    finally:
        local_conn.close()
        remote_session.close()

if __name__ == "__main__":
    migrate()
