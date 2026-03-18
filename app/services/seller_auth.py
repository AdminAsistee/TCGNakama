"""
Seller authentication service for TCG Nakama.
Handles password hashing, session creation, and auth dependencies.
"""
import hashlib
import os
import secrets
from datetime import datetime

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, SellerProfile


# Session secret — same pattern as admin auth in admin.py
SELLER_SESSION_SECRET = os.getenv("SESSION_SECRET", "")


# ── Password Utilities ──────────────────────────────────────────────────────

def generate_salt() -> str:
    """Generate a random 32-char hex salt."""
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    """SHA-256 hash with salt — consistent with existing admin auth pattern."""
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify a password against stored hash + salt."""
    return hash_password(password, salt) == stored_hash


# ── Session Utilities ────────────────────────────────────────────────────────

def create_seller_session_token(email: str) -> str:
    """Create a session token for a seller — same pattern as admin."""
    return hashlib.sha256(
        f"{email}{SELLER_SESSION_SECRET}".encode()
    ).hexdigest()[:32]


# ── FastAPI Dependencies ─────────────────────────────────────────────────────

async def get_seller_session(request: Request) -> User:
    """
    Dependency: verify seller session cookie and return the User object.
    Raises 302 redirect to /seller/login if not authenticated.
    """
    session_token = request.cookies.get("seller_session")
    if not session_token:
        raise HTTPException(status_code=302, headers={"Location": "/seller/login"})

    # Look up the user by checking all active sellers
    db = SessionLocal()
    try:
        users = db.query(User).filter(
            User.role == "seller",
            User.is_active == True
        ).all()

        for user in users:
            expected_token = create_seller_session_token(user.email)
            if session_token == expected_token:
                # Eagerly load seller_profile before closing session
                _ = user.seller_profile
                return user

        # No matching session found
        raise HTTPException(status_code=302, headers={"Location": "/seller/login"})
    finally:
        db.close()


async def get_current_user(request: Request) -> dict:
    """
    Unified dependency: checks BOTH admin and seller sessions.
    Returns a dict with role info for use in shared routes (Vault, Add Card, Upload).

    Returns:
        {"role": "admin", "email": str, "seller_id": None}
        {"role": "seller", "email": str, "seller_id": int, "seller_status": str, "store_name": str}

    Raises 302 to /seller/login if neither session is valid.
    """
    # 1. Check admin session first
    admin_session = request.cookies.get("admin_session")
    if admin_session:
        # Import SESSION_SECRET from admin router to avoid mismatch
        from app.routers.admin import SESSION_SECRET as ADMIN_SECRET
        stored_email = os.getenv("ADMIN_EMAIL", "admin@tcgnakama.com")
        expected_hash = hashlib.sha256(
            f"{stored_email}{ADMIN_SECRET}".encode()
        ).hexdigest()[:32]
        if admin_session == expected_hash:
            return {
                "role": "admin",
                "email": stored_email,
                "seller_id": None,
                "seller_status": None,
                "store_name": None,
            }

    # 2. Check seller session
    seller_session = request.cookies.get("seller_session")
    if seller_session:
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                User.role == "seller",
                User.is_active == True
            ).all()

            for user in users:
                expected_token = create_seller_session_token(user.email)
                if seller_session == expected_token:
                    profile = user.seller_profile
                    return {
                        "role": "seller",
                        "email": user.email,
                        "seller_id": user.id,
                        "seller_status": profile.status if profile else "pending",
                        "store_name": profile.store_name if profile else "",
                    }
        finally:
            db.close()

    # 3. Neither session valid
    raise HTTPException(status_code=302, headers={"Location": "/seller/login"})
