from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.dependencies import get_shopify_client, ShopifyClient
from urllib.parse import quote, unquote
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    page: int = Query(1, ge=1),
    client: ShopifyClient = Depends(get_shopify_client)
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
    # Removed print statement that could cause Unicode issues
    if len(v_ids) != len(set(v_ids)):
        print(f"WARNING: DUPLICATE VARIANT IDS DETECTED: {v_ids}")

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
    q: Optional[str] = None,
    collection: Optional[str] = None,
    rarity: Optional[str] = None,
    page: int = Query(1, ge=1),
    client: ShopifyClient = Depends(get_shopify_client)
):
    # Normalize for templates
    svr_active_collection = collection.strip().lower() if collection else None
    svr_active_rarity = rarity.strip().lower() if rarity else None

    # Apply filters during search
    if collection or rarity:
        products = await client.get_products(query=q, rarity=rarity)
        if collection:
            products = await client.get_collection_products(handle=collection)
            if q:
                products = [p for p in products if q.lower() in p['title'].lower()]
            if rarity:
                products = [p for p in products if p['rarity'].lower() == rarity.lower()]
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
    q: Optional[str] = None,
    rarity: Optional[str] = None,
    collection: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    client: ShopifyClient = Depends(get_shopify_client)
):
    # Normalize for templates
    svr_active_collection = collection.strip().lower() if collection else None
    svr_active_rarity = rarity.strip().lower() if rarity else None

    if collection:
        products = await client.get_collection_products(handle=collection)
        # Apply further filters if products were found in collection
        if q:
            products = [p for p in products if q.lower() in p['title'].lower()]
        if rarity:
            products = [p for p in products if p['rarity'].lower() == rarity.lower()]
        if min_price:
            products = [p for p in products if p['price'] >= min_price]
        if max_price:
            products = [p for p in products if p['price'] <= max_price]
    else:
        products = await client.get_products(query=q, rarity=rarity, min_price=min_price, max_price=max_price)
    
    collections = await client.get_collections()

    # Pagination
    PAGE_SIZE = 20
    total_products = len(products)
    total_pages = (total_products + PAGE_SIZE - 1) // PAGE_SIZE
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated_products = products[start:end]

    print(f"[DEBUG] Filter | collection: {svr_active_collection}, rarity: {svr_active_rarity}, page: {page}")
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
