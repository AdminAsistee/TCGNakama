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
    client: ShopifyClient = Depends(get_shopify_client)
):
    from app.dependencies import SHOPIFY_STORE_URL
    products = await client.get_products()
    
    # DEBUG: Check for duplicate variant IDs
    v_ids = [p.get('variant_id') for p in products]
    print(f"DEBUG: read_root | Products Count: {len(products)} | Unique Variant IDs: {len(set(v_ids))}")
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
        "products": products,
        "shopify_url": SHOPIFY_STORE_URL,
        "cart_count": cart_count,
        "checkout_url": checkout_url
    })

@router.get("/search", response_class=HTMLResponse)
async def search_products(
    request: Request,
    q: Optional[str] = None,
    client: ShopifyClient = Depends(get_shopify_client)
):
    products = await client.get_products(query=q)
    return templates.TemplateResponse("partials/product_grid.html", {"request": request, "products": products})

@router.get("/filter", response_class=HTMLResponse)
async def filter_products(
    request: Request,
    q: Optional[str] = None,
    rarity: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    client: ShopifyClient = Depends(get_shopify_client)
):
    products = await client.get_products(query=q, rarity=rarity, min_price=min_price, max_price=max_price)
    return templates.TemplateResponse("partials/product_grid.html", {"request": request, "products": products})

@router.get("/product/{product_id:path}", response_class=HTMLResponse)
async def get_product_detail(
    request: Request,
    product_id: str,
    client: ShopifyClient = Depends(get_shopify_client)
):
    product = await client.get_product(product_id)
    return templates.TemplateResponse("partials/product_modal.html", {"request": request, "product": product})

@router.post("/cart/add")
async def add_to_cart(
    request: Request,
    variant_id: str = Query(...),
    quantity: int = Query(1),
    client: ShopifyClient = Depends(get_shopify_client)
):
    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    print(f"DEBUG: add_to_cart | Existing cart_id: {cart_id} | Qty: {quantity}")
    
    if cart_id:
        cart = await client.add_to_existing_cart(cart_id, variant_id, quantity)
    else:
        cart = await client.create_cart(variant_id, quantity)
    
    total_q = cart.get("totalQuantity", 0)
    lines = cart.get("lines", {}).get("edges", [])
    if total_q == 0 and len(lines) > 0:
        total_q = sum(max(1, edge["node"]["quantity"]) for edge in lines)
    if total_q == 0: total_q = quantity # Fallback

    from app.dependencies import SHOPIFY_STORE_URL
    response = JSONResponse({
        "checkout_url": cart.get("checkoutUrl", f"{SHOPIFY_STORE_URL}/cart"),
        "total_quantity": total_q
    })
    
    if not cart_id and cart.get("id"):
        response.set_cookie(key="cart_id", value=quote(cart["id"]), max_age=3600*24*7, httponly=True, samesite="lax") 
        
    return response

@router.post("/cart/update")
async def update_cart_quantity(
    request: Request,
    line_id: str = Query(...),
    quantity: int = Query(...),
    client: ShopifyClient = Depends(get_shopify_client)
):
    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    
    if not cart_id:
        return JSONResponse({"status": "error", "message": "No cart"}, status_code=400)

    cart = await client.update_cart_line(cart_id, line_id, quantity)
    if not cart:
        return JSONResponse({"status": "error", "message": "Update failed"}, status_code=500)

    # Return updated drawer HTML
    items = []
    total_price = 0
    for edge in cart.get("lines", {}).get("edges", []):
        node = edge["node"]
        variant = node["merchandise"]
        product = variant["product"]
        tags = product.get("tags", [])
        rarity = "Common"
        card_set = "Unknown Set"
        for tag in tags:
            if tag.lower().startswith("rarity:"): rarity = tag.split(":")[1].strip()
            if tag.lower().startswith("set:"): card_set = tag.split(":")[1].strip()

        item_price = float(variant["price"]["amount"])
        item_qty = node["quantity"]
        items.append({
            "line_id": node["id"],
            "title": product["title"],
            "price": item_price,
            "quantity": item_qty,
            "image": product.get("featuredImage", {}).get("url") if product.get("featuredImage") else "https://images.pokemontcg.io/bg.jpg",
            "rarity": rarity,
            "set": card_set
        })
        total_price += item_price * item_qty

    return templates.TemplateResponse("partials/cart_drawer.html", {
        "request": request,
        "items": items,
        "total_price": total_price,
        "checkout_url": cart.get("checkoutUrl", "#"),
        "cart_count": cart.get("totalQuantity", 0)
    })

@router.post("/cart/clear")
async def clear_cart(
    request: Request,
    client: ShopifyClient = Depends(get_shopify_client)
):
    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    
    if not cart_id:
        return JSONResponse({"status": "error", "message": "No cart"}, status_code=400)

    cart = await client.clear_cart(cart_id)
    if not cart:
        return JSONResponse({"status": "error", "message": "Clear failed"}, status_code=500)

    # Return empty drawer HTML
    return templates.TemplateResponse("partials/cart_drawer.html", {
        "request": request,
        "items": [],
        "total_price": 0,
        "checkout_url": cart.get("checkoutUrl", "#"),
        "cart_count": 0
    })

@router.get("/cart/drawer", response_class=HTMLResponse)
async def get_cart_drawer(
    request: Request,
    client: ShopifyClient = Depends(get_shopify_client)
):
    cart_id_raw = request.cookies.get("cart_id")
    cart_id = unquote(cart_id_raw) if cart_id_raw else None
    print(f"DEBUG: get_cart_drawer | Request cart_id: {cart_id}")
    items = []
    total_price = 0
    checkout_url = "#"
    
    if cart_id:
        cart_data = await client.get_cart(cart_id)
        if cart_data:
            print(f"DEBUG: get_cart_drawer | Fetched cart lines count: {len(cart_data.get('lines', {}).get('edges', []))}")
            checkout_url = cart_data.get("checkoutUrl", "#")
            for edge in cart_data.get("lines", {}).get("edges", []):
                node = edge["node"]
                variant = node["merchandise"]
                product = variant["product"]
                
                # Parse tags for metadata
                tags = product.get("tags", [])
                rarity = "Common"
                card_set = "Unknown Set"
                for tag in tags:
                    if tag.lower().startswith("rarity:"):
                        rarity = tag.split(":")[1].strip()
                    elif tag.lower().startswith("set:"):
                        card_set = tag.split(":")[1].strip()

                items.append({
                    "line_id": node["id"],
                    "title": product["title"],
                    "price": float(variant["price"]["amount"]),
                    "quantity": max(1, node["quantity"]), # Force 1 for UI visibility
                    "image": product.get("featuredImage", {}).get("url") if product.get("featuredImage") else "https://images.pokemontcg.io/bg.jpg",
                    "rarity": rarity,
                    "set": card_set
                })
                total_price += float(variant["price"]["amount"]) * max(1, node["quantity"])

    return templates.TemplateResponse("partials/cart_drawer.html", {
        "request": request,
        "items": items,
        "total_price": total_price,
        "checkout_url": checkout_url
    })
