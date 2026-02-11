import os
import sqlalchemy
from sqlalchemy import inspect

# Use the connection string provide earlier
DATABASE_URL = "postgresql://db:AVNS_ZHMCwgpxwgIOeLPK5gt@app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com:25060/db?sslmode=require"

def verify_remote_tables():
    print(f"Connecting to remote database...")
    try:
        engine = sqlalchemy.create_engine(DATABASE_URL)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("\n--- Remote PostgreSQL Tables ---")
        if not tables:
            print("No tables found.")
        for table in tables:
            print(f"[OK] {table}")
        
        needed = ["banners", "product_costs", "product_grades", "search_logs"]
        missing = [t for t in needed if t not in tables]
        
        if not missing:
            print("\nSUCCESS: All required tables identified in production!")
        else:
            print(f"\nNOTE: Some tables are missing: {missing}")
            print("This is normal if the app hasn't restarted yet after your push.")

    except Exception as e:
        print(f"\nERROR: Could not connect to database: {e}")

if __name__ == "__main__":
    verify_remote_tables()
