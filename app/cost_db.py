"""
Local Cost Database
Stores buy prices and grades for products. Falls back to Shopify cost if available in future.
Supports SQLite (local) and PostgreSQL (production).
"""

import os
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, select
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Database configuration
db_url = os.getenv("DATABASE_URL", "")
if not db_url:
    # Default local path
    db_dir = Path(__file__).parent / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_dir}/costs.db"

# Fix for Render/DigitalOcean PostgreSQL URLs which might use "postgres://" instead of "postgresql://"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class ProductCost(Base):
    __tablename__ = "product_costs"
    product_id = Column(String, primary_key=True)
    buy_price = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProductGrade(Base):
    __tablename__ = "product_grades"
    product_id = Column(String, primary_key=True)
    grade = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SearchLog(Base):
    __tablename__ = "search_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String, nullable=False)
    results_count = Column(Integer, default=0)
    searched_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Initialize the database and create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

def get_cost(product_id: str) -> float | None:
    """Get the buy price for a product."""
    with SessionLocal() as session:
        cost = session.query(ProductCost).filter(ProductCost.product_id == product_id).first()
        return cost.buy_price if cost else None

def set_cost(product_id: str, buy_price: float) -> bool:
    """Set or update the buy price for a product."""
    with SessionLocal() as session:
        # Use upsert logic
        cost = session.query(ProductCost).filter(ProductCost.product_id == product_id).first()
        if cost:
            cost.buy_price = buy_price
        else:
            cost = ProductCost(product_id=product_id, buy_price=buy_price)
            session.add(cost)
        session.commit()
    return True

def get_all_costs() -> dict:
    """Get all product costs as a dictionary."""
    with SessionLocal() as session:
        costs = session.query(ProductCost).all()
        return {c.product_id: c.buy_price for c in costs}

def get_grade(product_id: str) -> str | None:
    """Get the grade for a product."""
    with SessionLocal() as session:
        grade = session.query(ProductGrade).filter(ProductGrade.product_id == product_id).first()
        return grade.grade if grade else None

def set_grade(product_id: str, grade: str) -> bool:
    """Set or update the grade for a product."""
    with SessionLocal() as session:
        item = session.query(ProductGrade).filter(ProductGrade.product_id == product_id).first()
        if item:
            item.grade = grade
        else:
            item = ProductGrade(product_id=product_id, grade=grade)
            session.add(item)
        session.commit()
    return True

def get_all_grades() -> dict:
    """Get all product grades as a dictionary."""
    with SessionLocal() as session:
        grades = session.query(ProductGrade).all()
        return {g.product_id: g.grade for g in grades}

def log_search(query: str, results_count: int = 0) -> bool:
    """Log a search query to the database."""
    with SessionLocal() as session:
        log = SearchLog(query=query.lower().strip(), results_count=results_count)
        session.add(log)
        session.commit()
    return True

def get_trending_searches(days: int = 30, limit: int = 10) -> list:
    """Get the most popular search queries from the last N days."""
    from sqlalchemy import func
    from datetime import timedelta
    
    threshold = datetime.utcnow() - timedelta(days=days)
    
    with SessionLocal() as session:
        results = session.query(
            SearchLog.query, 
            func.count(SearchLog.id).label('count')
        ).filter(SearchLog.searched_at >= threshold)\
         .group_by(SearchLog.query)\
         .order_by(func.count(SearchLog.id).desc())\
         .limit(limit)\
         .all()
        
        return [{"query": row[0], "count": row[1]} for row in results]

# Initialize DB on module load
init_db()
