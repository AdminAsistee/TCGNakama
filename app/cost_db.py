"""
Local Cost Database
Stores buy prices, grades, and physical locations for products.
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

class ValueSnapshot(Base):
    """Weekly inventory value snapshots for tracking changes over time."""
    __tablename__ = "value_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    week_label = Column(String, unique=True, nullable=False)  # e.g. "2026-W07"
    total_value = Column(Float, nullable=False)
    product_count = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProductLocation(Base):
    """Physical location / status of a card in inventory."""
    __tablename__ = "product_locations"
    product_id = Column(String, primary_key=True)
    location = Column(String, nullable=False, default="Folder")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Valid location categories
VALID_LOCATIONS = [
    "Display", "Folder", "Vault", "Grading", "Repair",
    "Mercari", "Consignment", "Sold-Pending", "Archived"
]

# Locations excluded from active inventory (total_value, live_count, snapshots)
INACTIVE_LOCATIONS = {"Archived", "Sold-Pending"}

# Default location for cards not yet assigned
DEFAULT_LOCATION = "Folder"

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

# --- Location CRUD ---

def get_location(product_id: str) -> str:
    """Get the location for a product. Returns DEFAULT_LOCATION if not set."""
    with SessionLocal() as session:
        loc = session.query(ProductLocation).filter(ProductLocation.product_id == product_id).first()
        return loc.location if loc else DEFAULT_LOCATION

def set_location(product_id: str, location: str) -> bool:
    """Set or update the location for a product. Validates against VALID_LOCATIONS."""
    if location not in VALID_LOCATIONS:
        raise ValueError(f"Invalid location '{location}'. Must be one of: {VALID_LOCATIONS}")
    with SessionLocal() as session:
        item = session.query(ProductLocation).filter(ProductLocation.product_id == product_id).first()
        if item:
            item.location = location
        else:
            item = ProductLocation(product_id=product_id, location=location)
            session.add(item)
        session.commit()
    return True

def get_all_locations() -> dict:
    """Get all product locations as a dictionary. Missing entries default to DEFAULT_LOCATION."""
    with SessionLocal() as session:
        locations = session.query(ProductLocation).all()
        return {loc.product_id: loc.location for loc in locations}

def is_active_location(product_id: str, all_locations: dict = None) -> bool:
    """Check if a product is in an active (non-archived/sold) location."""
    if all_locations is not None:
        location = all_locations.get(product_id, DEFAULT_LOCATION)
    else:
        location = get_location(product_id)
    return location not in INACTIVE_LOCATIONS

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


def save_value_snapshot(total_value: float, product_count: int = 0) -> bool:
    """Save or update this week's inventory value snapshot."""
    week_label = datetime.utcnow().strftime("%G-W%V")  # ISO year-week, e.g. "2026-W07"
    
    with SessionLocal() as session:
        snapshot = session.query(ValueSnapshot).filter(ValueSnapshot.week_label == week_label).first()
        if snapshot:
            snapshot.total_value = total_value
            snapshot.product_count = product_count
            snapshot.recorded_at = datetime.utcnow()
        else:
            snapshot = ValueSnapshot(
                week_label=week_label,
                total_value=total_value,
                product_count=product_count
            )
            session.add(snapshot)
        session.commit()
    return True


def get_value_history(limit: int = 12) -> list:
    """Get the last N weekly value snapshots, oldest first."""
    with SessionLocal() as session:
        snapshots = session.query(ValueSnapshot)\
            .order_by(ValueSnapshot.week_label.desc())\
            .limit(limit)\
            .all()
        
        # Reverse so oldest is first (for chart display)
        snapshots.reverse()
        
        return [{
            "week": s.week_label,
            "value": s.total_value,
            "count": s.product_count,
            "date": s.recorded_at.strftime("%b %d") if s.recorded_at else ""
        } for s in snapshots]


# Initialize DB on module load
init_db()

