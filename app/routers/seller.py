"""
Seller authentication routes for TCG Nakama.
Handles registration, login, and logout for sellers.
"""
import os
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import SessionLocal
from app.models import User, SellerProfile
from app.services.seller_auth import (
    generate_salt,
    hash_password,
    verify_password,
    create_seller_session_token,
    get_seller_session,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ── Registration ─────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Show the seller registration form."""
    return templates.TemplateResponse("seller/register.html", {
        "request": request,
        "error": None,
        "success": None,
    })


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    store_name: str = Form(...),
    location: str = Form(""),
):
    """Process seller registration."""
    # Validation
    email = email.strip().lower()
    store_name = store_name.strip()
    location = location.strip()

    if not email or not password or not store_name:
        return templates.TemplateResponse("seller/register.html", {
            "request": request,
            "error": "All required fields must be filled in.",
            "success": None,
        })

    if password != confirm_password:
        return templates.TemplateResponse("seller/register.html", {
            "request": request,
            "error": "Passwords do not match.",
            "success": None,
        })

    if len(password) < 8:
        return templates.TemplateResponse("seller/register.html", {
            "request": request,
            "error": "Password must be at least 8 characters.",
            "success": None,
        })

    db = SessionLocal()
    try:
        # Check if email already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return templates.TemplateResponse("seller/register.html", {
                "request": request,
                "error": "An account with this email already exists.",
                "success": None,
            })

        # Create user
        salt = generate_salt()
        user = User(
            email=email,
            password_hash=hash_password(password, salt),
            password_salt=salt,
            role="seller",
            is_active=True,
        )
        db.add(user)
        db.flush()  # Get user.id before creating profile

        # Create seller profile
        profile = SellerProfile(
            user_id=user.id,
            store_name=store_name,
            location=location if location else None,
            status="pending",
        )
        db.add(profile)
        db.commit()

        print(f"[SELLER] New seller registered: {email} (store: {store_name})")

        # Send confirmation email (non-blocking — failure doesn't break registration)
        try:
            from app.email_service import send_seller_registration_email
            send_seller_registration_email(to_email=email, store_name=store_name)
        except Exception as email_err:
            print(f"[SELLER] Registration email failed (non-fatal): {email_err}")

        return templates.TemplateResponse("seller/register.html", {
            "request": request,
            "error": None,
            "success": "Account created! Your application is pending admin approval. You can now log in to check your status.",
        })

    except Exception as e:
        db.rollback()
        print(f"[SELLER] Registration failed: {e}")
        return templates.TemplateResponse("seller/register.html", {
            "request": request,
            "error": "Registration failed. Please try again.",
            "success": None,
        })
    finally:
        db.close()


# ── Login ────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show the seller login form."""
    return templates.TemplateResponse("seller/login.html", {
        "request": request,
        "error": None,
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    """Authenticate seller and set session cookie."""
    email = email.strip().lower()

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email == email,
            User.role == "seller",
        ).first()

        if not user or not verify_password(password, user.password_hash, user.password_salt):
            return templates.TemplateResponse("seller/login.html", {
                "request": request,
                "error": "Invalid email or password.",
            })

        if not user.is_active:
            return templates.TemplateResponse("seller/login.html", {
                "request": request,
                "error": "This account has been deactivated.",
            })

        # Create session
        session_token = create_seller_session_token(user.email)
        response = RedirectResponse(url="/seller/dashboard", status_code=303)
        response.set_cookie(
            key="seller_session",
            value=session_token,
            httponly=True,
            max_age=86400,  # 24 hours
            samesite="lax",
        )

        print(f"[SELLER] Seller logged in: {email}")
        return response

    finally:
        db.close()


# ── Dashboard Gateway ────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def seller_dashboard(request: Request, user: "User" = Depends(get_seller_session)):
    """
    Seller dashboard gateway.
    - No seller_profile → redirect to login (edge case: corrupted registration)
    - status pending/rejected/suspended → show status screen
    - status approved → show the seller dashboard
    """
    profile = user.seller_profile
    if not profile:
        # Corrupted account — profile row missing
        return RedirectResponse(url="/seller/login", status_code=302)

    status = profile.status
    if status != "approved":
        return templates.TemplateResponse("seller/pending.html", {
            "request": request,
            "seller_status": status,
            "store_name": profile.store_name,
        })

    return templates.TemplateResponse("seller/dashboard.html", {
        "request": request,
        "store_name": profile.store_name,
        "email": user.email,
        "location": profile.location or "",
        "member_since": profile.created_at.strftime("%B %Y") if profile.created_at else "",
    })


# ── Status page (explicit named route) ──────────────────────────────────────

@router.get("/pending", response_class=HTMLResponse)
async def seller_pending(request: Request, user: "User" = Depends(get_seller_session)):
    """Explicit status route — redirects to dashboard gateway which handles routing."""
    return RedirectResponse(url="/seller/dashboard", status_code=302)


# ── Logout ───────────────────────────────────────────────────────────────────

@router.get("/logout")
async def logout():
    """Clear seller session and redirect to login."""
    response = RedirectResponse(url="/seller/login", status_code=303)
    response.delete_cookie("seller_session")
    return response
