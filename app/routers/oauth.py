"""
Shopify OAuth 2.0 Router
Handles authorization flow for Shopify Admin API access.
"""

import os
import secrets
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

router = APIRouter(prefix="/oauth", tags=["oauth"])

# Store state and tokens (in production, use a database)
oauth_state_store = {}
token_store = {}


def get_shop_name() -> str:
    """Extract shop name from SHOPIFY_STORE_URL."""
    url = os.getenv("SHOPIFY_STORE_URL", "")
    # Extract 'tcg-nakama-2' from 'https://tcg-nakama-2.myshopify.com/'
    if "myshopify.com" in url:
        return url.replace("https://", "").replace("http://", "").split(".myshopify.com")[0]
    return ""


@router.get("/authorize")
async def authorize(request: Request):
    """
    Step 1: Redirect user to Shopify authorization page.
    """
    shop = get_shop_name()
    if not shop:
        raise HTTPException(status_code=400, detail="SHOPIFY_STORE_URL not configured")
    
    api_key = os.getenv("SHOPIFY_API_KEY")
    scopes = os.getenv("SHOPIFY_SCOPES", "read_products,read_orders")
    redirect_uri = os.getenv("SHOPIFY_REDIRECT_URI", "http://localhost:8001/oauth/callback")
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_state_store[state] = True
    
    # Build authorization URL
    params = {
        "client_id": api_key,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    
    auth_url = f"https://{shop}.myshopify.com/admin/oauth/authorize?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(request: Request, code: str = None, state: str = None, shop: str = None):
    """
    Step 2: Exchange authorization code for access token.
    """
    # Validate state
    if state not in oauth_state_store:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Remove used state
    del oauth_state_store[state]
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")
    
    shop_name = get_shop_name()
    api_key = os.getenv("SHOPIFY_API_KEY")
    api_secret = os.getenv("SHOPIFY_API_SECRET")
    
    # Exchange code for access token
    token_url = f"https://{shop_name}.myshopify.com/admin/oauth/access_token"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            token_url,
            json={
                "client_id": api_key,
                "client_secret": api_secret,
                "code": code,
            }
        )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get access token: {response.text}"
        )
    
    data = response.json()
    access_token = data.get("access_token")
    
    # Store the token (in production, encrypt and store in database)
    token_store["admin_access_token"] = access_token
    
    # Save to environment for immediate use
    os.environ["SHOPIFY_ADMIN_TOKEN"] = access_token
    
    # Persist to .env for server restarts
    try:
        from dotenv import set_key
        set_key(".env", "SHOPIFY_ADMIN_TOKEN", access_token)
    except Exception as e:
        print(f"[ERROR] Failed to persist token to .env: {e}")
    
    # Redirect back to admin dashboard with success message
    response = RedirectResponse(url="/admin")
    
    # Automatically "log in" the admin by setting the session cookie
    import hashlib
    # Use the same secret as admin.py (or a default if not set)
    # Note: In a real app, this should be shared via a config module
    secret = os.getenv("SESSION_SECRET", "default_secret_change_me")
    stored_email = os.getenv("ADMIN_EMAIL", "admin@asistee.com")
    session_token = hashlib.sha256(f"{stored_email}{secret}".encode()).hexdigest()[:32]
    
    response.set_cookie(
        key="admin_session",
        value=session_token,
        httponly=True,
        max_age=3600 * 24 * 7, # 1 week
        samesite="lax" # Added samesite for security
    )
    
    return response


@router.get("/status")
async def status():
    """
    Check if we have a valid Admin API token.
    """
    token = token_store.get("admin_access_token") or os.getenv("SHOPIFY_ADMIN_TOKEN")
    return {
        "connected": bool(token),
        "token_preview": f"{token[:10]}..." if token else None
    }


def get_admin_token() -> str | None:
    """
    Helper function to get the current admin access token.
    Prioritizes SHOPIFY_ADMIN_TOKEN from environment if set correctly.
    """
    env_token = os.getenv("SHOPIFY_ADMIN_TOKEN")
    stored_token = token_store.get("admin_access_token")
    
    if env_token and env_token.startswith("shpat_"):
        print(f"[DEBUG] Using Admin Token from Environment (prefix: {env_token[:10]}...)")
        return env_token
    
    if stored_token:
        print(f"[DEBUG] Using Admin Token from token_store (prefix: {stored_token[:10]}...)")
        return stored_token
        
    if env_token:
        print(f"[DEBUG] Using Admin Token from Environment (prefix: {env_token[:10]}...)")
        return env_token
        
    print("[DEBUG] No Admin Token found!")
    return None
