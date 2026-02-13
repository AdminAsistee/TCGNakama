from typing import Optional, Any, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.dependencies import get_shopify_client, ShopifyClient
from app.routers.oauth import get_admin_token
from app import cost_db
from app.database import get_db
from app.models import Banner
from app.services import appraisal
from app.services.appraisal import safe_print
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
from collections import Counter
from itertools import combinations
import secrets
import httpx
import os
from pathlib import Path
from PIL import Image
import hashlib
from urllib.parse import quote, unquote


# Session secret for signing cookies
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(16))


async def fetch_shopify_orders(limit: int = 50) -> list:
    """Fetch orders from Shopify Admin API."""
    token = get_admin_token()
    if not token:
        return []
    
    shop_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
    api_version = "2024-01"
    
    url = f"{shop_url}/admin/api/{api_version}/orders.json?status=any&limit={limit}"
    headers = {"X-Shopify-Access-Token": token}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json().get("orders", [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch orders: {e}")
    return []


def analyze_customer_countries(orders: list) -> list:
    """Group orders by customer country."""
    country_counts = Counter()
    
    for order in orders:
        address = order.get("shipping_address") or order.get("billing_address") or {}
        country = address.get("country", "Unknown")
        if country:
            country_counts[country] += 1
    
    return [{"name": name, "count": count} for name, count in country_counts.most_common(10)]


def analyze_top_spenders(orders: list) -> list:
    """Calculate top customers by total spend."""
    spender_totals = {}
    
    for order in orders:
        customer = order.get("customer") or {}
        customer_id = customer.get("id")
        if not customer_id:
            continue
        
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or customer.get("email", "Unknown")
        total = float(order.get("total_price", 0))
        
        if customer_id not in spender_totals:
            spender_totals[customer_id] = {"name": name, "total": 0}
        spender_totals[customer_id]["total"] += total
    
    sorted_spenders = sorted(spender_totals.values(), key=lambda x: x["total"], reverse=True)
    
    # Format totals
    for s in sorted_spenders:
        s["total"] = f"{s['total']:,.0f}"
    
    return sorted_spenders[:10]


def analyze_basket_combinations(orders: list) -> list:
    """Find products frequently bought together."""
    pair_counts = Counter()
    
    for order in orders:
        line_items = order.get("line_items", [])
        product_titles = [item.get("title", "")[:30] for item in line_items]
        
        # Get all unique pairs
        for pair in combinations(set(product_titles), 2):
            sorted_pair = tuple(sorted(pair))
            pair_counts[sorted_pair] += 1
    
    # Convert to list format
    result = []
    for pair, count in pair_counts.most_common(5):
        if count >= 2:  # Only show pairs with 2+ occurrences
            result.append({
                "product1": pair[0],
                "product2": pair[1],
                "count": count
            })
    
    return result

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Add custom filter for URL-encoding Shopify GIDs (which contain slashes)
def urlencode_gid(value):
    """URL-encode a Shopify GID, encoding slashes and colons."""
    return quote(str(value), safe='')

templates.env.filters['urlencode_gid'] = urlencode_gid


def verify_session(request: Request) -> str:
    """Verify admin session from cookie."""
    session_token = request.cookies.get("admin_session")
    if not session_token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    
    # Simple token validation (in production, use signed tokens or JWT)
    expected_token = secrets.token_hex(16)  # This is regenerated, so we need to store/validate differently
    
    # For simplicity, we'll validate by checking if it matches our pattern
    # and verify it was signed with our secret
    stored_email = os.getenv("ADMIN_EMAIL", "admin@tcgnakama.com")
    expected_hash = hashlib.sha256(f"{stored_email}{SESSION_SECRET}".encode()).hexdigest()[:32]
    
    if session_token != expected_hash:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    
    return stored_email


async def get_admin_session(request: Request) -> str:
    """Dependency to check admin session, redirects to login if not authenticated."""
    session_token = request.cookies.get("admin_session")
    if not session_token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    
    stored_email = os.getenv("ADMIN_EMAIL", "admin@tcgnakama.com")
    expected_hash = hashlib.sha256(f"{stored_email}{SESSION_SECRET}".encode()).hexdigest()[:32]
    
    if session_token != expected_hash:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    
    return stored_email


class CostUpdate(BaseModel):
    product_id: str
    buy_price: float


class GradeUpdate(BaseModel):
    product_id: str
    grade: str


class BannerCreate(BaseModel):
    title: str
    subtitle: str
    cta_label: str
    cta_link: str
    gradient: str
    is_active: bool = True


class BannerUpdate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    cta_label: str | None = None
    cta_link: str | None = None
    gradient: str | None = None
    is_active: bool | None = None
    display_order: int | None = None


# Login page
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page."""
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    """Process login form."""
    correct_email = os.getenv("ADMIN_EMAIL", "admin@tcgnakama.com")
    correct_password = os.getenv("ADMIN_PASSWORD", "nakama2026")
    
    if email == correct_email and password == correct_password:
        # Create session token
        session_token = hashlib.sha256(f"{email}{SESSION_SECRET}".encode()).hexdigest()[:32]
        
        # Check if we have a valid Shopify token
        admin_token = get_admin_token()
        
        # Determine redirect target
        target_url = "/admin"
        if not admin_token or not admin_token.startswith("shpat_"):
            print("[DEBUG] No valid Admin Token found after login, redirecting to OAuth")
            target_url = "/oauth/authorize"
        
        response = RedirectResponse(url=target_url, status_code=303)
        response.set_cookie(
            key="admin_session",
            value=session_token,
            httponly=True,
            max_age=86400,  # 24 hours
            samesite="lax"
        )
        return response
    else:
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": "Invalid email or password"
        })




@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    query: Optional[str] = None,
    rarity: Optional[str] = None,
    page: int = 1,
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client)
):
    # Fetch real live data with search filters
    products = await client.get_products(query=query, rarity=rarity)
    
    # Get all costs and grades from local database
    all_costs = cost_db.get_all_costs()
    all_grades = cost_db.get_all_grades()
    
    # Calculate "Days in Vault" and attach costs for each product
    now = datetime.now(timezone.utc)
    for p in products:
        # Days in Vault calculation
        if p.get('createdAt'):
            try:
                created = datetime.fromisoformat(p['createdAt'].replace('Z', '+00:00'))
                delta = now - created
                p['days_in_vault'] = delta.days
            except Exception:
                p['days_in_vault'] = None
        else:
            p['days_in_vault'] = None
        
        # Attach buy_price from local DB
        product_id = p.get('id', '')
        p['buy_price'] = all_costs.get(product_id)
        
        # Calculate Gain/Loss percentage
        if p['buy_price'] and p['buy_price'] > 0:
            sell_price = p.get('price', 0)
            gain_loss = ((sell_price - p['buy_price']) / p['buy_price']) * 100
            p['gain_loss'] = round(gain_loss, 1)
        else:
            p['gain_loss'] = None
        
        # Attach grade from local DB
        p['grade'] = all_grades.get(product_id)
    
    # Calculate stats
    total_value = sum(p['price'] for p in products)
    live_count = len(products)
    vip_threshold = 100000
    vip_products = [p for p in products if p['price'] > vip_threshold]
    cart_value_vip = sum(p['price'] for p in vip_products)

    # Format currency for display
    def format_yen(val):
        return f"{int(val):,}"
    
    # Check OAuth connection status
    oauth_connected = bool(get_admin_token())
    
    # Pagination logic
    items_per_page = 20
    total_products = len(products)
    total_pages = (total_products + items_per_page - 1) // items_per_page  # Ceiling division
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages if total_pages > 0 else 1))
    
    # Calculate start and end indices
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    # Slice products for current page
    paginated_products = products[start_idx:end_idx]

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_value": format_yen(total_value),
        "live_count": live_count,
        "cart_value_vip": format_yen(cart_value_vip),
        "products": paginated_products,
        "current_query": query,
        "current_rarity": rarity,
        "oauth_connected": oauth_connected,
        "current_page": page,
        "total_pages": total_pages,
        "total_products": total_products
    })


@router.post("/cost")
async def save_cost(data: CostUpdate, admin: str = Depends(get_admin_session)):
    """Save a product's buy price to local database."""
    try:
        cost_db.set_cost(data.product_id, data.buy_price)
        return JSONResponse({"success": True, "message": "Cost saved"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/grade")
async def save_grade(data: GradeUpdate, admin: str = Depends(get_admin_session)):
    """Save a product's grade to local database."""
    try:
        cost_db.set_grade(data.product_id, data.grade)
        return JSONResponse({"success": True, "message": "Grade saved"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/appraise-market/{product_id}")
async def appraise_market_value(
    product_id: str,
    force_refresh: bool = False,  # Query parameter to bypass cache
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client)
):
    """Get market appraisal with JPY conversion for a specific product."""
    try:
        safe_print(f"[APPRAISE] Starting appraisal for product_id: {product_id} (force_refresh={force_refresh})")
        
        # Reconstruct full Shopify GID if only numeric ID provided
        if not product_id.startswith("gid://shopify/Product/"):
            product_id = f"gid://shopify/Product/{product_id}"
            safe_print(f"[APPRAISE] Reconstructed GID: {product_id}")
        
        # Fetch product from Shopify
        product = await client.get_product(product_id)
        
        if not product:
            safe_print(f"[APPRAISE] Product not found: {product_id}")
            return JSONResponse({'error': 'Product not found'}, status_code=404)
        
        # Extract card data
        card_name = product.get('title', 'Unknown')
        rarity = product.get('rarity', 'Common')
        
        # Extract set and card number from tags (using Shopify prefix format)
        tags = product.get('tags', [])
        # Handle both list and string formats
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(',')]
        elif isinstance(tags, list):
            tags = [str(tag).strip() for tag in tags]
        else:
            tags = []
        
        set_name = 'Unknown'
        card_number = ''
        
        # Extract from tags using prefix format (same as edit card function)
        for tag in tags:
            if tag.startswith("Set:"):
                set_name = tag.replace("Set:", "").strip()
            elif tag.startswith("Number:"):
                card_number = tag.replace("Number:", "").strip()
                # Add # prefix if not present
                if card_number and not card_number.startswith('#'):
                    card_number = f'#{card_number}'
        
        # If set_name is too short or looks like a variant code, ignore it
        if set_name and len(set_name) <= 3:
            set_name = ''
        
        print(f"[APPRAISE] Extracted from tags - Set: '{set_name}', Card Number: '{card_number}'")
        
        # Detect if Japanese card (has Japanese characters)
        import re
        has_japanese = bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', card_name))
        
        # Extract clean English card name from title
        # Title format: "ピカチュウ (Pikachu) - Pikachu sA #001/024"
        # We want: "Pikachu sA"
        search_name = card_name
        
        # Remove Japanese characters and parentheses
        search_name = re.sub(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\(\)]', '', search_name)
        
        # Remove card number pattern (#001/024 or similar)
        search_name = re.sub(r'#?\d+/\d+', '', search_name)
        
        # Remove extra dashes and whitespace
        search_name = re.sub(r'\s*-\s*', ' ', search_name).strip()
        search_name = ' '.join(search_name.split())  # Normalize whitespace
        
        print(f"[APPRAISE] Clean search name: '{search_name}'")
        safe_print(f"[APPRAISE] Card: {card_name}, Rarity: {rarity}, Set: {set_name}, Number: {card_number}, Japanese: {has_japanese}")
        
        # Detect variants from title
        variants = []
        title_upper = card_name.upper()
        if '1ST EDITION' in title_upper or 'FIRST EDITION' in title_upper:
            variants.append('1st Edition')
        if 'HOLO' in title_upper or 'HOLOGRAPHIC' in title_upper:
            variants.append('Holographic')
        if 'REVERSE' in title_upper:
            variants.append('Reverse Holo')
        if has_japanese:
            variants.append('Japanese')
        
        # Get market value in JPY
        safe_print(f"[APPRAISE] Calling appraisal service...")
        market_data = await appraisal.get_market_value_jpy(
            card_name=search_name,  # Use cleaned search name
            rarity=rarity,
            set_name=set_name,
            card_number=card_number,
            variants=variants if variants else None,
            force_refresh=force_refresh  # Pass through force_refresh parameter
        )
        
        safe_print(f"[APPRAISE] Market data: {market_data}")
        
        if 'error' in market_data:
            safe_print(f"[APPRAISE] Error in market data: {market_data['error']}")
            return JSONResponse(market_data, status_code=500)
        
        # Get actual price and compare
        actual_price = float(product.get('price', 0))
        market_jpy = market_data['market_jpy']
        
        comparison = await appraisal.compare_price_to_market(actual_price, market_jpy)
        
        # Combine results
        result = {
            **market_data,
            'actual_price': int(actual_price),
            'price_diff_pct': comparison['difference_pct'],
            'status': comparison['status'],
            'recommendation': comparison['recommendation']
        }
        
        safe_print(f"[APPRAISE] Success! Result: {result}")
        return JSONResponse(
            result,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    except Exception as e:
        # Safely handle exception with potential Unicode characters
        try:
            error_msg = f"[APPRAISE] Exception: {type(e).__name__}: {str(e)}"
            safe_print(error_msg)
        except:
            # If even safe_print fails, use basic ASCII
            print(f"[APPRAISE] Exception occurred (Unicode error in message)")
        
        # Return error without Unicode characters
        error_str = str(e).encode('ascii', 'replace').decode('ascii')
        return JSONResponse({'error': f'Appraisal failed: {error_str}'}, status_code=500)




@router.get("/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request, admin: str = Depends(get_admin_session), client: ShopifyClient = Depends(get_shopify_client)):
    products = await client.get_products()
    
    # Get grades and costs from local DB
    all_grades = cost_db.get_all_grades()
    all_costs = cost_db.get_all_costs()
    
    # Get trending searches
    trending_searches = cost_db.get_trending_searches(days=30, limit=10)
    
    # Calculate PSA 10 candidates
    def calculate_grading_score(product, grade):
        score = 0
        # Grade weight (40 points)
        if grade == 'S': score += 40
        elif grade == 'A': score += 30
        elif grade == 'B': score += 15
        
        # Value weight (30 points) - cards above ¥5000
        price = float(product.get('price', 0))
        if price > 5000: score += 30
        elif price > 2000: score += 20
        elif price > 500: score += 10
        
        # Rarity weight (15 points)
        title = product.get('title', '').upper()
        if 'SR' in title or 'UR' in title or 'SAR' in title:
            score += 15
        elif 'VMAX' in title or 'VSTAR' in title:
            score += 12
        elif 'V' in title or 'R' in title:
            score += 8
        
        # Stock bonus (15 points) - prioritize multiple copies
        stock = product.get('stock', 1)
        if stock >= 3: score += 15
        elif stock >= 2: score += 10
        else: score += 5
        
        return min(score, 100)  # Cap at 100%
    
    # Build PSA candidates list
    psa_candidates = []
    total_graded = 0
    for product in products:
        product_id = product.get('id', '')
        grade = all_grades.get(product_id)
        
        if grade:
            total_graded += 1
        
        if grade in ['S', 'A']:  # Only S and A grades are PSA candidates
            score = calculate_grading_score(product, grade)
            psa_candidates.append({
                'title': product.get('title', 'Unknown'),
                'grade': grade,
                'price': product.get('price', 0),
                'score': score
            })
    
    # Sort by score and take top 10
    psa_candidates.sort(key=lambda x: x['score'], reverse=True)
    psa_candidates = psa_candidates[:10]
    
    # Fetch order data from Shopify Admin API
    orders = await fetch_shopify_orders(limit=50)
    countries = analyze_customer_countries(orders)
    top_spenders = analyze_top_spenders(orders)
    bundles = analyze_basket_combinations(orders)
    
    return templates.TemplateResponse("admin/analytics.html", {
        "request": request,
        "products": products,
        "psa_candidates": psa_candidates,
        "trending_searches": trending_searches,
        "total_graded": total_graded,
        "countries": countries,
        "top_spenders": top_spenders,
        "bundles": bundles,
        "orders_count": len(orders)
    })


@router.post("/sync")
async def force_sync(request: Request, admin: str = Depends(get_admin_session), client: ShopifyClient = Depends(get_shopify_client)):
    """Triggers a manual refresh of Shopify data."""
    try:
        await client.get_products()
    except Exception as e:
        print(f"Sync failed: {e}")
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/estimate-market-value")
async def estimate_market_value(
    card_name: str,
    set_name: str = "",
    card_number: str = "",
    rarity: str = "",
    admin: str = Depends(get_admin_session)
):
    """
    Estimate market value for a card based on its details.
    Used by the add card form after AI image appraisal.
    
    Note: card_name should be the clean English name (e.g., "Monkey D. Luffy")
    already extracted by the AI, not the full formatted title.
    """
    try:
        from app.services.appraisal import get_market_value_jpy
        
        safe_print(f"[ESTIMATE] ===== Market Value Estimation Request =====")
        safe_print(f"[ESTIMATE] card_name: '{card_name}'")
        safe_print(f"[ESTIMATE] set_name: '{set_name}'")
        safe_print(f"[ESTIMATE] card_number: '{card_number}'")
        safe_print(f"[ESTIMATE] rarity: '{rarity}'")
        safe_print(f"[ESTIMATE] ==========================================")
        
        # Call the market value estimation service
        # card_name is already clean English name from AI extraction
        market_data = await get_market_value_jpy(
            card_name=card_name,
            rarity=rarity,
            set_name=set_name,
            card_number=card_number,
            variants=None,  # No variant detection from image appraisal
            force_refresh=True  # Always get fresh data for new cards
        )
        
        safe_print(f"[ESTIMATE] Market data: {market_data}")
        
        return JSONResponse({
            'success': True,
            'market_value_jpy': market_data.get('market_jpy'),  # Fixed: was market_value_jpy
            'market_value_usd': market_data.get('market_usd'),  # Fixed: was market_value_usd
            'source': market_data.get('source', 'estimated'),
            'debug': {
                'search_params': {
                    'card_name': card_name,
                    'set_name': set_name,
                    'card_number': card_number,
                    'rarity': rarity
                },
                'raw_response': market_data
            }
        })
        
    except Exception as e:
        safe_print(f"[ESTIMATE] Error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({
            'success': False,
            'error': str(e)
        }, status_code=500)


@router.get("/check-duplicate-card")
async def check_duplicate_card(
    card_name: str,
    current_product_id: Optional[str] = None,  # ID of product being edited (to exclude from check)
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client)
):
    """
    Check if a card with the same name already exists in Shopify.
    Returns duplicate status and product info if found.
    Matches both card name and card number (e.g., "027/071") if present.
    
    Args:
        card_name: The card name to check
        current_product_id: Optional product ID being edited (will be excluded from duplicate check)
    """
    try:
        import re
        
        safe_print(f"[DUPLICATE_CHECK] Checking for duplicate: '{card_name}'")
        if current_product_id:
            safe_print(f"[DUPLICATE_CHECK] Excluding current product: {current_product_id}")
        
        # STEP 1: Extract card number FIRST from the original input
        # Extract card number pattern - supports multiple formats:
        # - Pokemon with hash: #027/071
        # - One Piece: #OP09-051, #ST01-001
        # - Pokemon without hash: 027/071
        # - Simple numbered: #123
        # Order matters: longer/more specific patterns first!
        card_number_pattern = re.search(r'(#\d{1,4}/\d{1,4}|#[A-Z]{2,4}\d{2,4}-\d{3}|\d{1,4}/\d{1,4}|#\d{1,4})', card_name)
        card_number = card_number_pattern.group(0) if card_number_pattern else None
        
        # STEP 2: Extract the clean card name (remove everything except the character/card name)
        # Start fresh from original input
        clean_card_name = card_name
        
        # Remove the card number if found
        if card_number:
            clean_card_name = clean_card_name.replace(card_number, '')
        
        # Remove parentheses/brackets content (like language translations)
        clean_card_name = re.sub(r'\s*[\(\[].*?[\)\]]', '', clean_card_name)
        
        # Remove set names (everything after dash)
        clean_card_name = re.sub(r'\s*[-–—]\s*.*$', '', clean_card_name)
        
        # Clean up extra whitespace
        clean_card_name = clean_card_name.strip()
        
        safe_print(f"[DUPLICATE_CHECK] Extracted - Name: '{clean_card_name}', Number: '{card_number}'")
        
        # Search strategy: Use card number if available (more specific), otherwise use card name
        # This is much faster than fetching all products
        if card_number:
            search_query = card_number
            safe_print(f"[DUPLICATE_CHECK] Searching by card number: '{search_query}'")
        else:
            search_query = clean_card_name
            safe_print(f"[DUPLICATE_CHECK] Searching by card name: '{search_query}'")
        
        products = await client.get_products(query=search_query)
        
        safe_print(f"[DUPLICATE_CHECK] Found {len(products)} products matching '{search_query}'")
        
        # Define Unicode normalization function (handles accented characters)
        import unicodedata
        def normalize_text(text):
            # NFD = decompose accented chars, then filter out combining marks
            nfd = unicodedata.normalize('NFD', text)
            return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
        
        # Check for match by card name and card number
        matches_found = 0
        for product in products:
            product_id = str(product.get('id', ''))
            product_title = product.get('title', '')
            product_title_lower = product_title.lower()
            
            # Skip if this is the current product being edited
            if current_product_id and product_id == current_product_id:
                safe_print(f"[DUPLICATE_CHECK] Skipping current product: {product_title}")
                continue
            
            # Check if card name is in the product title (accent-insensitive)
            normalized_clean_name = normalize_text(clean_card_name.lower())
            normalized_product_title = normalize_text(product_title_lower)
            name_matches = normalized_clean_name in normalized_product_title
            
            # Check if card number is in the product title (if we have a card number)
            number_matches = True  # Default to true if no card number
            if card_number:
                number_matches = card_number in product_title
            
            # Log each product check for debugging
            if name_matches or number_matches:
                safe_print(f"[DUPLICATE_CHECK] Checking: {product_title}")
                safe_print(f"[DUPLICATE_CHECK]   Clean name: '{clean_card_name}' -> normalized: '{normalized_clean_name}'")
                safe_print(f"[DUPLICATE_CHECK]   Card number: '{card_number}'")
                safe_print(f"[DUPLICATE_CHECK]   Name match: {name_matches}, Number match: {number_matches}")
            
            # Both must match
            if name_matches and number_matches:
                matches_found += 1
                safe_print(f"[DUPLICATE_CHECK] ✓✓✓ DUPLICATE FOUND #{matches_found}: {product_title} (ID: {product.get('id')})")
                return JSONResponse({
                    'exists': True,
                    'product_id': str(product.get('id')),
                    'product_title': product_title
                })
        
        safe_print(f"[DUPLICATE_CHECK] No duplicate found after checking {len(products)} products")
        return JSONResponse({
            'exists': False,
            'product_id': None,
            'product_title': None
        })
    except Exception as e:
        safe_print(f"[DUPLICATE_CHECK] Error: {e}")
        return JSONResponse({
            'exists': False,
            'product_id': None,
            'product_title': None,
            'error': str(e)
        })



@router.post("/appraise-card-image")
async def appraise_card_image(
    request: Request,
    admin: str = Depends(get_admin_session),
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None)
):
    """
    Appraise a card from an uploaded image or URL using Gemini AI vision.
    Returns extracted card details for form auto-population.
    """
    try:
        safe_print("[APPRAISE_IMAGE] Received appraisal request")
        
        # Validate that we have either a file or URL
        if not image_file and not image_url:
            return JSONResponse(
                {'error': 'Please provide either an image file or image URL'},
                status_code=400
            )
        
        # Prepare image data
        image_data = None
        url_to_use = None
        
        if image_file and image_file.filename:
            # Read uploaded file
            safe_print(f"[APPRAISE_IMAGE] Processing uploaded file: {image_file.filename}")
            image_data = await image_file.read()
        elif image_url:
            # Use URL directly
            safe_print(f"[APPRAISE_IMAGE] Processing image URL: {image_url}")
            url_to_use = image_url
        
        # Call appraisal service
        result = await appraisal.appraise_card_from_image(
            image_data=image_data,
            image_url=url_to_use
        )
        
        if 'error' in result:
            safe_print(f"[APPRAISE_IMAGE] Error: {result['error']}")
            return JSONResponse(result, status_code=500)
        
        safe_print(f"[APPRAISE_IMAGE] Success: {result}")
        return JSONResponse({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        safe_print(f"[APPRAISE_IMAGE] Exception: {e}")
        return JSONResponse(
            {'error': f'Appraisal failed: {str(e)}'},
            status_code=500
        )



@router.get("/add-card", response_class=HTMLResponse)
async def add_card_page(
    request: Request, 
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client)
):
    """Show the add card form."""
    admin_token = get_admin_token()
    categories = []
    if admin_token:
        try:
            categories = await client.get_collections(admin_token)
        except Exception as e:
            print(f"Error fetching categories: {e}")
    
    # Fallback to defaults if empty
    if not categories:
        categories = ["Pokémon", "One Piece", "Magic: TG", "Yu-Gi-Oh!"]
        
    return templates.TemplateResponse("admin/add_card.html", {
        "request": request,
        "categories": categories
    })


@router.get("/add-card/success")
async def add_card_success(
    request: Request,
    admin: str = Depends(get_admin_session)
):
    """Display success page after adding a card."""
    return templates.TemplateResponse("admin/add_card_success.html", {
        "request": request
    })


@router.get("/edit-card", response_class=HTMLResponse)
async def edit_card_page(
    request: Request,
    product_id: str,
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client)
):
    """Show the add card form pre-populated with existing product data for editing."""
    try:
        print(f"[EDIT_CARD] Attempting to fetch product: {product_id}")
        
        # Fetch product data
        product = await client.get_product(product_id)
        
        if not product:
            # Product not found - this could mean:
            # 1. Product doesn't exist in Shopify
            # 2. API permissions issue
            # 3. Product was deleted
            error_msg = f"Unable to load product for editing. Product ID: {product_id}. The product may have been deleted or there may be an API issue. Check server logs for details."
            print(f"[EDIT_CARD] ERROR: Product not found for ID: {product_id}")
            return templates.TemplateResponse("admin/add_card.html", {
                "request": request,
                "error": error_msg,
                "categories": []
            })
        
        # Fetch collections for dropdowns
        admin_token = get_admin_token()
        categories = []
        if admin_token:
            try:
                categories = await client.get_collections(admin_token)
            except Exception as e:
                print(f"Error fetching categories: {e}")
        
        if not categories:
            categories = ["Pokémon", "One Piece", "Magic: TG", "Yu-Gi-Oh!"]
        
        # Get vendor from product data
        vendor = product.get("vendor", "TCG Nakama")
        
        # Extract metadata from tags
        condition = "Booster Pack"  # default
        rarity = product.get("rarity", "Common")  # default from _map_product
        set_name = product.get("set", "")  # default from _map_product
        card_number = product.get("card_number", "")  # default from _map_product
        
        # Get collections - already extracted by _map_product
        product_collections = product.get("collections", [])
        
        # Extract values from tags (these override the defaults from _map_product)
        for tag in product.get("tags", []):
            if tag.startswith("Condition:"):
                condition = tag.replace("Condition:", "").strip()
            elif tag.startswith("Rarity:"):
                rarity = tag.replace("Rarity:", "").strip()
            elif tag.startswith("Set:"):
                set_name = tag.replace("Set:", "").strip()
            elif tag.startswith("Number:"):
                card_number = tag.replace("Number:", "").strip()
        
        # Extract image URLs - images are already in the correct format from _map_product
        image_urls = product.get("images", [])
        
        # Store extracted values in product dict for template access
        product["vendor"] = vendor
        product["condition"] = condition
        product["rarity"] = rarity
        product["set"] = set_name
        product["card_number"] = card_number
        product["image_urls"] = image_urls
        
        # Fetch buy_price from local database
        from app import cost_db
        buy_price = cost_db.get_cost(product_id)
        product["buy_price"] = buy_price
        
        return templates.TemplateResponse("admin/add_card.html", {
            "request": request,
            "edit_mode": True,
            "product": product,
            "categories": categories,
            "vendor": vendor,
            "product_collections": product_collections
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[EDIT_CARD] EXCEPTION: {e}")
        print(f"[EDIT_CARD] TRACEBACK:\n{error_trace}")
        return templates.TemplateResponse("admin/add_card.html", {
            "request": request,
            "error": f"Error loading product for editing: {str(e)}. Check server logs for full traceback.",
            "categories": []
        })


@router.post("/add-card")
async def add_card(
    request: Request,
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client),
    name: str = Form(...),
    price: float = Form(...),
    collections: List[str] = Form([]),
    vendor: str = Form("TCG Nakama"),
    set_name: str = Form(...),
    card_number: str = Form(...),
    rarity: str = Form(...),
    condition: str = Form(...),
    description: str = Form(""),
    stock: int = Form(1),
    buy_price: Optional[float] = Form(None),
    image_urls: List[str] = Form([]),
    image_files: List[UploadFile] = File([])
):
    """Process the add card form and sync to Shopify."""
    admin_token = get_admin_token()
    if not admin_token:
        # In a real app, we'd redirect to OAuth or show a better error
        return templates.TemplateResponse("admin/add_card.html", {
            "request": request,
            "error": "Shopify Admin API not connected. Please connect Shopify first."
        })

    # Collect all image sources
    all_images = [url for url in image_urls if url.strip()]
    
    print(f"[DEBUG] Attempting to add card. Token prefix: {admin_token[:10]}...")
    
    # Process file uploads
    for file in image_files:
        if file.filename:
            try:
                content = await file.read()
                if len(content) > 0:
                    # 1. Create staged upload
                    target = await client.staged_uploads_create(
                        admin_token=admin_token,
                        filename=file.filename,
                        mime_type=file.content_type,
                        file_size=str(len(content))
                    )
                    
                    # 2. Upload file
                    resource_url = await client.upload_file_to_staged_target(
                        target=target,
                        file_content=content,
                        mime_type=file.content_type
                    )
                    all_images.append(resource_url)
            except Exception as upload_err:
                print(f"[ERROR] Failed to upload {file.filename}: {upload_err}")

    # Prepare tags for Shopify
    tags = [
        f"Set: {set_name}",
        f"Rarity: {rarity.capitalize()}",
        f"Number: {card_number}",
        f"Condition: {condition}"
    ]
    
    # Convert newlines to HTML breaks for description
    description_html = description.replace('\n', '<br>').replace('\r', '') if description else ""
    
    product_data = {
        "title": name,
        "description": description_html,
        "price": price,
        "vendor": vendor,
        "product_type": collections[0] if collections else "Trading Card",
        "tags": tags,
        "quantity": stock,
        "images": all_images,
        "collections": collections
    }

    try:
        # 1. Create product in Shopify
        new_product = await client.create_product(admin_token, product_data)
        shopify_product_id = new_product["id"]

        # 2. Save Buy Price (Cost) to local DB if provided
        if buy_price is not None:
            cost_db.set_cost(shopify_product_id, buy_price)
            
        return RedirectResponse(url="/admin/add-card/success", status_code=303)
    except Exception as e:
        print(f"[ERROR] Failed to add card: {str(e).encode('ascii', 'backslashreplace').decode()}")
        return templates.TemplateResponse("admin/add_card.html", {
            "request": request,
            "error": f"Failed to add card: {str(e)}"
        })


@router.post("/update-card")
async def update_card(
    request: Request,
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client),
    product_id: str = Form(...),
    variant_id: str = Form(...),
    name: str = Form(...),
    price: float = Form(...),
    set_name: str = Form(...),
    rarity: str = Form(...),
    card_number: str = Form(...),
    vendor: str = Form(...),
    condition: str = Form(...),
    description: str = Form(""),
    stock: int = Form(1),
    collections: List[str] = Form([]),
    image_urls: List[str] = Form([]),
    image_files: List[UploadFile] = File([]),
    buy_price: Optional[float] = Form(None)
):
    """Process the edit card form and update product in Shopify."""
    admin_token = get_admin_token()
    if not admin_token:
        return templates.TemplateResponse("admin/add_card.html", {
            "request": request,
            "error": "Shopify Admin API not connected."
        })
    
    # Separate existing Shopify images from new images
    # existing_images_to_keep: Shopify CDN URLs that are still in the form (user didn't delete them)
    # new_images_to_add: New uploaded files or external URLs
    existing_images_to_keep = []
    new_images_to_add = []
    
    for url in image_urls:
        url_stripped = url.strip()
        if url_stripped:
            if 'cdn.shopify.com' in url_stripped:
                # This is an existing Shopify image that user wants to keep
                existing_images_to_keep.append(url_stripped)
            else:
                # This is a new external URL
                new_images_to_add.append(url_stripped)
    
    # Process file uploads
    for file in image_files:
        if file.filename:
            try:
                content = await file.read()
                if len(content) > 0:
                    # 1. Create staged upload
                    target = await client.staged_uploads_create(
                        admin_token=admin_token,
                        filename=file.filename,
                        mime_type=file.content_type,
                        file_size=str(len(content))
                    )
                    
                    # 2. Upload file
                    resource_url = await client.upload_file_to_staged_target(
                        target=target,
                        file_content=content,
                        mime_type=file.content_type
                    )
                    new_images_to_add.append(resource_url)
                    print(f"[DEBUG] Uploaded file {file.filename}, resource URL: {resource_url}")
            except Exception as upload_err:
                print(f"[ERROR] Failed to upload {file.filename}: {upload_err}")
    
    print(f"[DEBUG] Updating product {product_id}")
    print(f"[DEBUG] Existing images to KEEP (from form): {existing_images_to_keep}")
    print(f"[DEBUG] NEW images to ADD: {new_images_to_add}")
    print(f"[DEBUG] Collections: {collections}")
    
    # Prepare tags - ONLY include Set, Rarity, Number, Condition
    # Do NOT include vendor or collections as they have their own fields
    tags = [
        f"Set: {set_name}",
        f"Rarity: {rarity.capitalize()}",
        f"Number: {card_number}",
        f"Condition: {condition}"
    ]
    
    description_html = description.replace('\n', '<br>')
    
    # Update product with separate lists for existing vs new images
    try:
        success = await client.update_product(
            product_id=product_id,
            title=name,
            description=description_html,
            price=price,
            tags=tags,
            vendor=vendor,
            images_to_keep=existing_images_to_keep,
            images_to_add=new_images_to_add,
            collections=collections if collections else None
        )
    except Exception as e:
        safe_print(f"[ERROR] Exception during update_product: {e}")
        return templates.TemplateResponse("admin/add_card.html", {
            "request": request,
            "error": f"Failed to update product: {str(e)}"
        })
    
    if not success:
        safe_print(f"[ERROR] update_product returned False for product_id: {product_id}")
        return templates.TemplateResponse("admin/add_card.html", {
            "request": request,
            "error": "Failed to update product - check server logs for details"
        })
    
    # Update inventory
    try:
        # First, get the inventory_item_id from the variant
        variant_query = f"""
        query {{
          productVariant(id: "{variant_id}") {{
            inventoryItem {{
              id
            }}
          }}
        }}
        """
        
        shop_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
        admin_url = f"{shop_url}/admin/api/2024-01/graphql.json"
        headers = {"X-Shopify-Access-Token": admin_token, "Content-Type": "application/json"}
        
        import httpx
        async with httpx.AsyncClient() as http_client:
            variant_response = await http_client.post(admin_url, json={"query": variant_query}, headers=headers)
            variant_data = variant_response.json()
            
            if variant_data.get("data", {}).get("productVariant", {}).get("inventoryItem"):
                inventory_item_id = variant_data["data"]["productVariant"]["inventoryItem"]["id"]
                await client._update_inventory(admin_token, inventory_item_id, stock)
            else:
                print(f"[ERROR] Could not get inventory_item_id from variant")
    except Exception as e:
        print(f"[ERROR] Failed to update inventory: {e}")
    
    # Update buy_price in local database
    if buy_price is not None:
        from app import cost_db
        cost_db.set_cost(product_id, buy_price)
        print(f"[DEBUG] Updated buy_price to {buy_price} for product {product_id}")
    
    # Redirect to success page with product info
    from urllib.parse import quote
    return RedirectResponse(url=f"/admin/edit-success?product_id={quote(product_id)}&product_name={quote(name)}", status_code=303)


@router.get("/edit-success", response_class=HTMLResponse)
async def edit_success(
    request: Request,
    product_id: str,
    product_name: str,
    admin: str = Depends(get_admin_session)
):
    """Display success page after editing a card."""
    return templates.TemplateResponse("admin/edit_success.html", {
        "request": request,
        "product_id": product_id,
        "product_name": product_name
    })


@router.post("/delete-card")
async def delete_card(
    request: Request,
    product_id: str = Form(...),
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client)
):
    """Delete a card from Shopify and local database."""
    print(f"[DEBUG] Deleting product: {product_id}")
    
    # Delete from Shopify
    success = await client.delete_product(product_id)
    
    if success:
        # Delete buy_price from local database
        from app import cost_db
        try:
            # Note: cost_db might not have a delete method, so we'll set it to None or 0
            cost_db.set_cost(product_id, 0)
            print(f"[DEBUG] Cleared buy_price for product {product_id}")
        except Exception as e:
            print(f"[WARNING] Could not clear buy_price: {e}")
        
        print(f"[SUCCESS] Product {product_id} deleted successfully")
    else:
        print(f"[ERROR] Failed to delete product {product_id}")
    
    # Redirect back to dashboard
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/refresh")
async def refresh_shopify(
    admin: str = Depends(get_admin_session)
):
    """Manually trigger Shopify product sync."""
    from app.background_tasks import sync_shopify_products, get_sync_status
    
    try:
        # Trigger sync
        await sync_shopify_products()
        status = get_sync_status()
        
        return JSONResponse({
            "success": True,
            "message": "Products synced successfully",
            "last_sync": status["last_sync"]
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/logout")
async def logout():
    """Clear session cookie and redirect to marketplace."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="admin_session")
    return response


# ============= BANNER MANAGEMENT ENDPOINTS =============

@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    admin: str = Depends(get_admin_session),
    db: Session = Depends(get_db)
):
    """Admin settings page with banner management."""
    banners_query = db.query(Banner).order_by(Banner.display_order).all()
    
    # Convert SQLAlchemy models to dictionaries for JSON serialization in template
    banners = []
    for banner in banners_query:
        banners.append({
            'id': banner.id,
            'title': banner.title,
            'subtitle': banner.subtitle,
            'cta_label': banner.cta_label,
            'cta_link': banner.cta_link,
            'gradient': banner.gradient,
            'image_path': banner.image_path,
            'is_active': banner.is_active,
            'display_order': banner.display_order
        })
    
    # Available gradient options for dropdown
    gradient_options = [
        "from-red-900 via-orange-900 to-amber-900",
        "from-violet-900 via-purple-900 to-indigo-900",
        "from-sky-900 via-cyan-900 to-teal-900",
        "from-emerald-900 via-green-900 to-lime-900",
        "from-pink-900 via-rose-900 to-red-900",
        "from-yellow-900 via-amber-900 to-orange-900",
        "from-blue-900 via-indigo-900 to-purple-900",
    ]
    
    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "banners": banners,
        "gradient_options": gradient_options
    })


@router.post("/banners/upload")
async def upload_banner_image(
    file: UploadFile = File(...),
    admin: str = Depends(get_admin_session)
):
    """Upload a banner image."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        return JSONResponse(
            {"success": False, "error": "Invalid file type. Only JPEG, PNG, and WebP are allowed."},
            status_code=400
        )
    
    try:
        # Create banners directory if it doesn't exist
        banner_dir = Path("app/static/banners")
        banner_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(datetime.now().timestamp())
        file_ext = Path(file.filename).suffix
        filename = f"banner_{timestamp}{file_ext}"
        filepath = banner_dir / filename
        
        # Save uploaded file
        contents = await file.read()
        
        # Open with Pillow to validate and optionally resize
        img = Image.open(io.BytesIO(contents))
        
        # Resize if too large (recommended: 1920x600px)
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Save optimized image
        img.save(filepath, quality=85, optimize=True)
        
        # Return relative path
        relative_path = f"/static/banners/{filename}"
        
        return JSONResponse({
            "success": True,
            "image_path": relative_path,
            "filename": filename
        })
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/banners")
async def create_banner(
    title: str = Form(...),
    subtitle: str = Form(...),
    cta_label: str = Form(...),
    cta_link: str = Form(...),
    gradient: str = Form(...),
    image_path: str | None = Form(None),
    is_active: bool = Form(True),
    admin: str = Depends(get_admin_session),
    db: Session = Depends(get_db)
):
    """Create a new banner."""
    try:
        # Get max display_order
        max_order = db.query(Banner).count()
        
        banner = Banner(
            title=title,
            subtitle=subtitle,
            cta_label=cta_label,
            cta_link=cta_link,
            gradient=gradient,
            image_path=image_path if image_path else None,
            display_order=max_order + 1,
            is_active=is_active
        )
        
        db.add(banner)
        db.commit()
        
        return RedirectResponse(url="/admin/settings", status_code=303)
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/banners/{banner_id}")
async def update_banner(
    banner_id: int,
    title: str = Form(None),
    subtitle: str = Form(None),
    cta_label: str = Form(None),
    cta_link: str = Form(None),
    gradient: str = Form(None),
    image_path: str = Form(None),
    is_active: bool = Form(None),
    admin: str = Depends(get_admin_session),
    db: Session = Depends(get_db)
):
    """Update an existing banner."""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    if title is not None:
        banner.title = title
    if subtitle is not None:
        banner.subtitle = subtitle
    if cta_label is not None:
        banner.cta_label = cta_label
    if cta_link is not None:
        banner.cta_link = cta_link
    if gradient is not None:
        banner.gradient = gradient
    if image_path is not None:
        banner.image_path = image_path if image_path else None
    if is_active is not None:
        banner.is_active = is_active
    
    banner.updated_at = datetime.utcnow()
    db.commit()
    
    return RedirectResponse(url="/admin/settings", status_code=303)


@router.post("/banners/{banner_id}/toggle")
async def toggle_banner(
    banner_id: int,
    admin: str = Depends(get_admin_session),
    db: Session = Depends(get_db)
):
    """Toggle banner active status."""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.is_active = not banner.is_active
    banner.updated_at = datetime.utcnow()
    db.commit()
    
    return JSONResponse({"success": True, "is_active": banner.is_active})


@router.delete("/banners/{banner_id}")
async def delete_banner(
    banner_id: int,
    admin: str = Depends(get_admin_session),
    db: Session = Depends(get_db)
):
    """Delete a banner."""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    # Delete image file if exists
    if banner.image_path:
        try:
            file_path = Path(f"app{banner.image_path}")
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Error deleting image file: {e}")
    
    db.delete(banner)
    db.commit()
    
    return JSONResponse({"success": True})


@router.post("/banners/reorder")
async def reorder_banners(
    request: Request,
    admin: str = Depends(get_admin_session),
    db: Session = Depends(get_db)
):
    """Reorder banners based on new order array."""
    data = await request.json()
    banner_ids = data.get("banner_ids", [])
    
    for index, banner_id in enumerate(banner_ids):
        banner = db.query(Banner).filter(Banner.id == banner_id).first()
        if banner:
            banner.display_order = index + 1
            banner.updated_at = datetime.utcnow()
    
    db.commit()
    
    return JSONResponse({"success": True})


# Add missing import for io
import io
