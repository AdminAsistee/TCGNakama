from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.dependencies import get_shopify_client, ShopifyClient
from app.database import get_db
from typing import Optional, Union
from app.models import Banner
from sqlalchemy.orm import Session
from urllib.parse import quote, unquote
from typing import Optional
from datetime import datetime, timezone
import random

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")




def _calc_listed_ago(product: dict) -> str:
    """Calculate human-readable time since product was listed."""
    created = product.get('createdAt', '')
    if not created:
        return "Recently"
    try:
        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        delta = datetime.now(timezone.utc) - created_dt
        minutes = int(delta.total_seconds() / 60)
        if minutes < 1:
            return "Just now"
        elif minutes < 60:
            return f"{minutes}m ago"
        elif minutes < 1440:
            return f"{minutes // 60}h ago"
        else:
            return f"{minutes // 1440}d ago"
    except Exception:
        return "Recently"


@router.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    page: int = Query(1, ge=1),
    client: ShopifyClient = Depends(get_shopify_client),
    db: Session = Depends(get_db)
):
    from app.dependencies import SHOPIFY_STORE_URL
    products = await client.get_products()
    
    # Pagination
    PAGE_SIZE = 20
    total_products = len(products)
    total_pages = (total_products + PAGE_SIZE - 1) // PAGE_SIZE
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated_products = products[start:end]

    collections = await client.get_collections()
    
    # DEBUG: Check for duplicate variant IDs
    v_ids = [p.get('variant_id') for p in products]
    if len(v_ids) != len(set(v_ids)):
        print(f"WARNING: DUPLICATE VARIANT IDS DETECTED: {v_ids}")

    # Add time-since-listed to each product
    for p in products:
        p['listed_ago'] = _calc_listed_ago(p)
    
    # Fresh Pulls: newest 6 products (sorted by createdAt desc)
    fresh_pulls = sorted(products, key=lambda x: x.get('createdAt', ''), reverse=True)[:6]
    
    # What's Hot: top 6 highest priced products with growth indicators
    hot_picks = sorted(products, key=lambda x: x.get('price', 0), reverse=True)[:6]
    for hp in hot_picks:
        hp['growth'] = round(random.uniform(1.5, 5.5), 1)
        hp['hype_pct'] = random.randint(60, 95)
    
    # Featured collection for hero banner
    featured_collection = collections[0] if collections else None
    
    # Fetch active banners from database
    banners = db.query(Banner).filter(
        Banner.is_active == True
    ).order_by(Banner.display_order).all()
    
    # Convert to dict format for template
    banner_dicts = [b.to_dict() for b in banners]

    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    cart_count = 0
    checkout_url = f"{SHOPIFY_STORE_URL}/cart"
    
    if cart_id:
        cart_data = await client.get_cart(cart_id)
        if cart_data:
            cart_count = cart_data.get("totalQuantity", 0)
            checkout_url = cart_data.get("checkoutUrl", checkout_url)

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "products": paginated_products,
        "fresh_pulls": fresh_pulls,
        "hot_picks": hot_picks,
        "banners": banner_dicts,
        "featured_collection": featured_collection,
        "collections": collections,
        "shopify_url": SHOPIFY_STORE_URL,
        "cart_count": cart_count,
        "checkout_url": checkout_url,
        "svr_active_collection": None,
        "svr_active_rarity": None,
        "current_page": page,
        "total_pages": total_pages,
        "total_products": total_products
    })

@router.get("/search", response_class=HTMLResponse)
async def search_products(
    request: Request,
    q: str = Query(default=""),
    collection: str = Query(default=""),
    rarity: str = Query(default=""),
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    client: ShopifyClient = Depends(get_shopify_client)
):
    # Convert empty strings to None
    q = q.strip() if q and q.strip() else None
    rarity = rarity.strip() if rarity and rarity.strip() else None
    collection = collection.strip() if collection and collection.strip() else None
    
    # Normalize for templates
    svr_active_collection = collection.lower() if collection else None
    svr_active_rarity = rarity.lower() if rarity else None

    # Apply filters during search
    if collection or rarity or max_price:
        products = await client.get_products(query=q, rarity=rarity, max_price=max_price)
        if collection:
            products = await client.get_collection_products(handle=collection)
            if q:
                products = [p for p in products if q.lower() in p['title'].lower()]
            if rarity:
                products = [p for p in products if p['rarity'].lower() == rarity.lower()]
            if max_price:
                products = [p for p in products if p['price'] <= max_price]
    else:
        products = await client.get_products(query=q)

    collections = await client.get_collections()
    
    # Pagination
    PAGE_SIZE = 20
    total_products = len(products)
    total_pages = (total_products + PAGE_SIZE - 1) // PAGE_SIZE
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated_products = products[start:end]

    print(f"[DEBUG] Search | collection: {svr_active_collection}, rarity: {svr_active_rarity}, page: {page}")
    return templates.TemplateResponse("partials/product_grid.html", {
        "request": request, 
        "products": paginated_products,
        "collections": collections,
        "svr_active_collection": svr_active_collection,
        "svr_active_rarity": svr_active_rarity,
        "current_page": page,
        "total_pages": total_pages,
        "total_products": total_products
    })

@router.get("/filter", response_class=HTMLResponse)
async def filter_products(
    request: Request,
    q: str = Query(default=""),
    rarity: str = Query(default=""),
    collection: str = Query(default=""),
    condition: str = Query(default=""),
    min_price: Union[str, float, None] = Query(default=None),
    max_price: Union[str, float, None] = Query(default=None),
    page: int = Query(1, ge=1),
    client: ShopifyClient = Depends(get_shopify_client)
):
    # Convert empty strings to None
    q = q.strip() if q and q.strip() else None
    rarity = rarity.strip() if rarity and rarity.strip() else None
    collection = collection.strip() if collection and collection.strip() else None
    condition = condition.strip() if condition and condition.strip() else None
    
    # Convert price parameters
    if isinstance(min_price, str) and not min_price.strip():
        min_price = None
    elif isinstance(min_price, str):
        min_price = float(min_price)
    
    if isinstance(max_price, str) and not max_price.strip():
        max_price = None
    elif isinstance(max_price, str):
        max_price = float(max_price)
    
    # Normalize for templates
    svr_active_collection = collection.lower() if collection else None
    svr_active_rarity = rarity.lower() if rarity else None
    svr_active_condition = condition if condition else None

    if collection:
        products = await client.get_collection_products(handle=collection)
        # Apply further filters if products were found in collection
        if q:
            products = [p for p in products if q.lower() in p['title'].lower()]
        if rarity:
            products = [p for p in products if p['rarity'].lower() == rarity.lower()]
        if condition:
            products = [p for p in products if f"Condition: {condition}" in p.get('tags', [])]
        if min_price:
            products = [p for p in products if p['price'] >= min_price]
        if max_price:
            products = [p for p in products if p['price'] <= max_price]
    else:
        products = await client.get_products(query=q, rarity=rarity, min_price=min_price, max_price=max_price)
        # Apply condition filter to general products
        if condition:
            products = [p for p in products if f"Condition: {condition}" in p.get('tags', [])]
    
    collections = await client.get_collections()

    # Pagination
    PAGE_SIZE = 20
    total_products = len(products)
    total_pages = (total_products + PAGE_SIZE - 1) // PAGE_SIZE
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated_products = products[start:end]

    print(f"[DEBUG] Filter | q: {q}, rarity: {svr_active_rarity}, collection: {svr_active_collection}, condition: {svr_active_condition}, max_price: {max_price}")
    return templates.TemplateResponse("partials/product_grid.html", {
        "request": request, 
        "products": paginated_products,
        "collections": collections,
        "svr_active_collection": svr_active_collection,
        "svr_active_rarity": svr_active_rarity,
        "svr_active_condition": svr_active_condition,
        "current_page": page,
        "total_pages": total_pages,
        "total_products": total_products
    })

@router.get("/product/{product_id:path}", response_class=HTMLResponse)
async def get_product_details(
    request: Request,
    product_id: str,
    client: ShopifyClient = Depends(get_shopify_client)
):
    product = await client.get_product(product_id)
    return templates.TemplateResponse("partials/product_modal.html", {
        "request": request,
        "product": product
    })

# --- CART OPERATIONS ---

def _get_cart_context(cart_data: dict):
    if not cart_data:
        return {"items": [], "total_price": 0, "cart_count": 0}
    
    items = []
    total_price = 0
    for edge in cart_data.get("lines", {}).get("edges", []):
        node = edge["node"]
        variant = node.get("merchandise", {})
        product = variant.get("product", {})
        
        # Extract metadata from tags
        tags = product.get("tags", [])
        card_set = "Unknown Set"
        rarity = "Common"
        for tag in tags:
            if tag.lower().startswith("set:"): card_set = tag.split(":")[1].strip()
            if tag.lower().startswith("rarity:"): rarity = tag.split(":")[1].strip()

        price = float(variant.get("price", {}).get("amount", 0))
        qty = node.get("quantity", 0)
        items.append({
            "line_id": node.get("id"),
            "variant_id": variant.get("id"),
            "title": product.get("title", variant.get("title")),
            "image": product.get("featuredImage", {}).get("url") if product.get("featuredImage") else "https://images.pokemontcg.io/bg.jpg",
            "price": price,
            "quantity": qty,
            "set": card_set,
            "rarity": rarity
        })
        total_price += price * qty
        
    return {
        "items": items,
        "total_price": total_price,
        "cart_count": cart_data.get("totalQuantity", 0)
    }

@router.post("/cart/add", response_class=JSONResponse)
async def add_to_cart(
    request: Request,
    variant_id: str,
    quantity: int = 1,
    client: ShopifyClient = Depends(get_shopify_client)
):
    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    
    if cart_id:
        cart = await client.add_to_existing_cart(cart_id, variant_id, quantity)
    else:
        cart = await client.create_cart(variant_id, quantity)
    
    if not cart:
        return JSONResponse({
            "status": "error",
            "message": "Could not create or update cart"
        }, status_code=500)

    response = JSONResponse({
        "status": "success",
        "total_quantity": cart.get("totalQuantity", 0),
        "checkout_url": cart.get("checkoutUrl")
    })
    
    if not cart_id:
        response.set_cookie(
            key="cart_id",
            value=quote(cart["id"]),
            httponly=True,
            samesite="lax"
        )
    return response

@router.get("/cart/drawer", response_class=HTMLResponse)
async def get_cart_drawer(
    request: Request,
    client: ShopifyClient = Depends(get_shopify_client)
):
    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    
    cart_data = await client.get_cart(cart_id) if cart_id else None
    context = _get_cart_context(cart_data)
    
    return templates.TemplateResponse("partials/cart_drawer.html", {
        "request": request,
        **context,
        "checkout_url": cart_data.get("checkoutUrl") if cart_data else "#"
    })

@router.post("/cart/update", response_class=HTMLResponse)
async def update_cart(
    line_id: str,
    quantity: int,
    request: Request,
    client: ShopifyClient = Depends(get_shopify_client)
):
    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    
    if cart_id:
        await client.update_cart_line(cart_id, line_id, quantity)
            
    # Refresh drawer
    return await get_cart_drawer(request, client)

@router.post("/cart/clear", response_class=HTMLResponse)
async def clear_cart(
    request: Request,
    client: ShopifyClient = Depends(get_shopify_client)
):
    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    
    if cart_id:
        await client.clear_cart(cart_id)
        
    return await get_cart_drawer(request, client)
