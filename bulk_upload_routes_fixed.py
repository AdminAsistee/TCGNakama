# ============================================================================
# BULK UPLOAD ROUTES
# ============================================================================

@router.get("/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_page(request: Request, admin: str = Depends(get_admin_session)):
    """Show bulk card upload page."""
    return templates.TemplateResponse("admin/bulk_upload.html", {"request": request})


@router.post("/bulk-upload/appraise")
async def bulk_upload_appraise(
    request: Request,
    images: List[UploadFile] = File(...),
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client)
):
    """
    Phase 1: Appraise multiple card images.
    Returns appraisal data for each card with 'exists' flag.
    """
    results = []
    from app.services.shopify_auth import get_admin_token as _dynamic_token
    admin_token = await _dynamic_token()
    if not admin_token:
        admin_token = os.getenv("SHOPIFY_ADMIN_TOKEN")
    
    # Create temp directory for uploads
    temp_dir = Path("app/static/uploads/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, image_file in enumerate(images):
        try:
            # Save image temporarily
            file_ext = Path(image_file.filename).suffix
            temp_filename = f"bulk_{datetime.now().timestamp()}_{idx}{file_ext}"
            temp_path = temp_dir / temp_filename
            
            # Read and save file
            content = await image_file.read()
            with open(temp_path, "wb") as f:
                f.write(content)
            
            # Appraise the card using image bytes
            appraisal_result = await appraisal.appraise_card_from_image(image_data=content)
            
            if appraisal_result.get("error"):
                results.append({
                    "error": appraisal_result["error"],
                    "image_url": f"/static/uploads/temp/{temp_filename}",
                    "filename": image_file.filename
                })
                continue
            
            # Extract card details
            card_name = appraisal_result.get("card_name", "Unknown")
            set_name = appraisal_result.get("set_name", "")
            card_number = appraisal_result.get("card_number", "")
            rarity = appraisal_result.get("rarity", "")
            vendor = appraisal_result.get("manufacturer", "TCG Nakama")
            card_condition = appraisal_result.get("card_condition", "Near Mint")
            full_set_name = appraisal_result.get("full_set_name", "")
            
            # Check if card exists in Shopify (by card number + name)
            exists = False
            shopify_product_id = None
            shopify_variant_id = None
            shopify_inventory_item_id = None
            price = None
            current_quantity = 0
            
            if card_number and card_name and admin_token:
                existing_product = await client.search_product_by_card(
                    admin_token, 
                    card_number, 
                    card_name
                )
                if existing_product:
                    exists = True
                    shopify_product_id = existing_product["product_id"]
                    shopify_variant_id = existing_product["variant_id"]
                    shopify_inventory_item_id = existing_product["inventory_item_id"]
                    current_quantity = existing_product.get("current_quantity", 0)
                    price = existing_product.get("price")
                    safe_print(f"[BULK_UPLOAD] Found existing product: {existing_product['title']}, price: ${price}, current qty: {current_quantity}")
            
            # If card is new, fetch price from PriceCharting
            if not exists:
                try:
                    price_result = await appraisal.get_market_value_jpy(
                        card_name=card_name,
                        rarity=rarity,
                        set_name=set_name,
                        card_number=card_number
                    )
                    if not price_result.get("error"):
                        price = price_result.get("market_jpy")
                        safe_print(f"[BULK_UPLOAD] PriceCharting price for {card_name}: ¥{price}")
                except Exception as price_error:
                    safe_print(f"[BULK_UPLOAD] Could not fetch price from PriceCharting: {price_error}")
            
            results.append({
                "card_name": card_name,
                "set_name": set_name,
                "card_number": card_number,
                "rarity": rarity,
                "vendor": vendor,
                "card_condition": card_condition,
                "full_set_name": full_set_name,
                "price": price,
                "exists": exists,
                "shopify_product_id": shopify_product_id,
                "shopify_variant_id": shopify_variant_id,
                "shopify_inventory_item_id": shopify_inventory_item_id,
                "current_quantity": current_quantity,
                "image_url": f"/static/uploads/temp/{temp_filename}",
                "temp_path": str(temp_path),
                "filename": image_file.filename
            })
            
        except Exception as e:
            safe_print(f"[BULK_UPLOAD] Error appraising {image_file.filename}: {e}")
            results.append({
                "error": str(e),
                "image_url": "",
                "filename": image_file.filename
            })
    
    return JSONResponse(results)


@router.post("/bulk-upload/confirm")
async def bulk_confirm(
    request: Request,
    admin: str = Depends(get_admin_session),
    client: ShopifyClient = Depends(get_shopify_client)
):
    """
    Phase 2: Confirm and add selected cards to Shopify.
    For existing cards: increment inventory
    For new cards: create product
    """
    body = await request.json()
    selected_cards = body.get("cards", [])
    
    results = []
    from app.services.shopify_auth import get_admin_token as _dynamic_token
    admin_token = await _dynamic_token()
    if not admin_token:
        admin_token = os.getenv("SHOPIFY_ADMIN_TOKEN")
    
    for card in selected_cards:
        try:
            card_name = card.get("card_name")
            set_name = card.get("set_name", "")
            card_number = card.get("card_number", "")
            rarity = card.get("rarity", "")
            vendor = card.get("vendor", "TCG Nakama")
            price = card.get("price", 0)
            quantity = int(card.get("quantity", 1))
            exists = card.get("exists", False)
            shopify_inventory_item_id = card.get("shopify_inventory_item_id")
            current_quantity = int(card.get("current_quantity", 0))
            temp_path = card.get("temp_path")
            card_condition = card.get("card_condition", "Near Mint")
            full_set_name = card.get("full_set_name", "")
            condition = card.get("condition", "Raw")
            
            if exists and shopify_inventory_item_id:
                # Update existing product inventory
                new_quantity = current_quantity + quantity
                safe_print(f"[BULK_UPLOAD] Updating inventory for {card_name}: {current_quantity} + {quantity} = {new_quantity}")
                
                try:
                    await client._update_inventory(admin_token, shopify_inventory_item_id, new_quantity)
                    safe_print(f"[BULK_UPLOAD] Successfully incremented inventory for {card_name}")
                    results.append({
                        "success": True,
                        "card_name": card_name,
                        "action": "inventory_updated",
                        "quantity": quantity
                    })
                except Exception as inv_error:
                    safe_print(f"[BULK_UPLOAD] Error updating inventory: {inv_error}")
                    results.append({
                        "success": False,
                        "card_name": card_name,
                        "error": f"Failed to update inventory: {str(inv_error)}"
                    })
            else:
                # Create new product in Shopify
                safe_print(f"[BULK_UPLOAD] Creating new product for {card_name}")
                
                try:
                    # Prepare product data
                    product_title = card_name.strip()
                    tags = []
                    if rarity:
                        tags.append(f"Rarity: {rarity.capitalize()}")
                    if set_name:
                        tags.append(f"Set: {set_name}")
                    if full_set_name:
                        tags.append(f"Set Name: {full_set_name}")
                    if card_condition:
                        tags.append(f"Card: {card_condition}")
                    if condition:
                        tags.append(f"Condition: {condition}")
                    if card_number:
                        tags.append(f"Number: {card_number}")
                    
                    description_html = f"<p><strong>Set:</strong> {set_name}</p>" if set_name else ""
                    description_html += f"<p><strong>Card Number:</strong> {card_number}</p>" if card_number else ""
                    description_html += f"<p><strong>Rarity:</strong> {rarity}</p>" if rarity else ""
                    
                    product_data = {
                        "title": product_title,
                        "description": description_html,
                        "price": price if price else 0,
                        "vendor": vendor if vendor else "TCG Nakama",
                        "product_type": "Trading Card",
                        "tags": tags,
                        "quantity": quantity,
                        "images": []
                    }
                    
                    # Upload image if available
                    if temp_path and Path(temp_path).exists():
                        with open(temp_path, "rb") as img_file:
                            img_data = img_file.read()
                            product_data["images"] = [{"data": img_data}]
                    
                    created_product = await client.create_product(admin_token, product_data)
                    safe_print(f"[BULK_UPLOAD] Successfully created product: {created_product.get('id')}")
                    
                    results.append({
                        "success": True,
                        "card_name": card_name,
                        "action": "product_created",
                        "product_id": created_product["id"]
                    })
                except Exception as create_error:
                    safe_print(f"[BULK_UPLOAD] Error creating product: {create_error}")
                    results.append({
                        "success": False,
                        "card_name": card_name,
                        "error": f"Failed to create product: {str(create_error)}"
                    })
            
            # Clean up temp file
            if temp_path and Path(temp_path).exists():
                try:
                    Path(temp_path).unlink()
                except Exception as cleanup_error:
                    safe_print(f"[BULK_UPLOAD] Error cleaning up temp file: {cleanup_error}")
                
        except Exception as e:
            safe_print(f"[BULK_UPLOAD] Error processing {card.get('card_name', 'unknown')}: {e}")
            results.append({
                "success": False,
                "card_name": card.get("card_name", "Unknown"),
                "error": str(e)
            })
    
    return JSONResponse(results)
