"""
Local Cost Database
Stores buy prices and grades for products. Falls back to Shopify cost if available in future.
"""

import sqlite3
import os
from pathlib import Path

# Database path
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "costs.db"


def init_db():
    """Initialize the database and create tables if they don't exist."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_costs (
            product_id TEXT PRIMARY KEY,
            buy_price REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_grades (
            product_id TEXT PRIMARY KEY,
            grade TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            results_count INTEGER DEFAULT 0,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def get_cost(product_id: str) -> float | None:
    """Get the buy price for a product."""
    if not DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT buy_price FROM product_costs WHERE product_id = ?",
        (product_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None


def set_cost(product_id: str, buy_price: float) -> bool:
    """Set or update the buy price for a product."""
    init_db()  # Ensure DB exists
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO product_costs (product_id, buy_price, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(product_id) DO UPDATE SET
            buy_price = excluded.buy_price,
            updated_at = CURRENT_TIMESTAMP
    """, (product_id, buy_price))
    
    conn.commit()
    conn.close()
    return True


def get_all_costs() -> dict:
    """Get all product costs as a dictionary."""
    if not DB_PATH.exists():
        return {}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT product_id, buy_price FROM product_costs")
    results = cursor.fetchall()
    conn.close()
    
    return {row[0]: row[1] for row in results}


# Grade functions
def get_grade(product_id: str) -> str | None:
    """Get the grade for a product."""
    if not DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT grade FROM product_grades WHERE product_id = ?",
        (product_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None


def set_grade(product_id: str, grade: str) -> bool:
    """Set or update the grade for a product."""
    init_db()  # Ensure DB exists
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO product_grades (product_id, grade, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(product_id) DO UPDATE SET
            grade = excluded.grade,
            updated_at = CURRENT_TIMESTAMP
    """, (product_id, grade))
    
    conn.commit()
    conn.close()
    return True


def get_all_grades() -> dict:
    """Get all product grades as a dictionary."""
    if not DB_PATH.exists():
        return {}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT product_id, grade FROM product_grades")
    results = cursor.fetchall()
    conn.close()
    
    return {row[0]: row[1] for row in results}


# Search logging functions
def log_search(query: str, results_count: int = 0) -> bool:
    """Log a search query to the database."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO search_logs (query, results_count)
        VALUES (?, ?)
    """, (query.lower().strip(), results_count))
    
    conn.commit()
    conn.close()
    return True


def get_trending_searches(days: int = 30, limit: int = 10) -> list:
    """Get the most popular search queries from the last N days."""
    if not DB_PATH.exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT query, COUNT(*) as count
        FROM search_logs
        WHERE searched_at >= datetime('now', ?)
        GROUP BY query
        ORDER BY count DESC
        LIMIT ?
    """, (f'-{days} days', limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return [{"query": row[0], "count": row[1]} for row in results]


# Initialize DB on module load
init_db()
