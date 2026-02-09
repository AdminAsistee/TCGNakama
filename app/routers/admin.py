from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.dependencies import get_shopify_client, ShopifyClient
from app.routers.oauth import get_admin_token
from app import cost_db
from datetime import datetime, timezone
from pydantic import BaseModel
from collections import Counter
from itertools import combinations
import secrets
import httpx
import os


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


def verify_session(request: Request) -> str:
    """Verify admin session from cookie."""
    session_token = request.cookies.get("admin_session")
    if not session_token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    
    # Simple token validation (in production, use signed tokens or JWT)
    expected_token = secrets.token_hex(16)  # This is regenerated, so we need to store/validate differently
    
    # For simplicity, we'll validate by checking if it matches our pattern
    # and verify it was signed with our secret
    import hashlib
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
    import hashlib
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
        import hashlib
        session_token = hashlib.sha256(f"{email}{SESSION_SECRET}".encode()).hexdigest()[:32]
        
        response = RedirectResponse(url="/admin", status_code=303)
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


class CostUpdate(BaseModel):
    product_id: str
    buy_price: float


class GradeUpdate(BaseModel):
    product_id: str
    grade: str


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    query: str = None,
    rarity: str = None,
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

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_value": format_yen(total_value),
        "live_count": live_count,
        "cart_value_vip": format_yen(cart_value_vip),
        "products": products,
        "current_query": query,
        "current_rarity": rarity,
        "oauth_connected": oauth_connected
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


@router.get("/logout")
async def logout():
    """Clear session cookie and redirect to marketplace."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="admin_session")
    return response

