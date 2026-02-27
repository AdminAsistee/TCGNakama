# Bulk Upload Routes

@router.get("/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_page(request: Request, admin: str = Depends(get_admin_session)):
    """Show bulk card upload page."""
    return templates.TemplateResponse("admin/bulk_upload.html", {"request": request})


@router.post("/bulk-upload/appraise")
async def bulk_appraise(
    request: Request,
    images: List[UploadFile] = File(...),
    admin: str = Depends(get_admin_session)
):
    """
    Phase 1: Appraise multiple card images.
    Returns appraisal data for each card with 'exists' flag.
    """
    results = []
    
    # Create temp directory for uploads
    temp_dir = Path("app/static/uploads/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, image_file in enumerate(images):
        try:
            # Save image temporarily as WebP
            temp_filename = f"bulk_{datetime.now().timestamp()}_{idx}.webp"
            temp_path = temp_dir / temp_filename

            # Read, convert to WebP, and save
            content = await image_file.read()
            from app.utils.image_utils import convert_to_webp
            webp_content = convert_to_webp(content)
            temp_path.write_bytes(webp_content)
            
            # Appraise the card
            appraisal_result = await appraisal.appraise_card_from_image(str(temp_path))
            
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
            price = appraisal_result.get("price")
            
            # Check if card exists in Shopify (by card number + name)
            exists = False
            shopify_product_id = None
            
            # TODO: Implement Shopify product search by card name + number
            # For now, we'll assume all cards are new
            
            results.append({
                "card_name": card_name,
                "set_name": set_name,
                "card_number": card_number,
                "rarity": rarity,
                "price": price,
                "exists": exists,
                "shopify_product_id": shopify_product_id,
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
    
    for card in selected_cards:
        try:
            card_name = card.get("card_name")
            set_name = card.get("set_name", "")
            card_number = card.get("card_number", "")
            rarity = card.get("rarity", "")
            price = card.get("price")
            quantity = card.get("quantity", 1)
            exists = card.get("exists", False)
            shopify_product_id = card.get("shopify_product_id")
            temp_path = card.get("temp_path")
            
            if exists and shopify_product_id:
                # Update existing product inventory
                # TODO: Implement inventory increment
                safe_print(f"[BULK_UPLOAD] Incrementing inventory for {card_name} by {quantity}")
                results.append({
                    "success": True,
                    "card_name": card_name,
                    "action": "inventory_updated"
                })
            else:
                # Create new product in Shopify
                # TODO: Implement product creation
                safe_print(f"[BULK_UPLOAD] Creating new product for {card_name}")
                results.append({
                    "success": True,
                    "card_name": card_name,
                    "action": "product_created"
                })
            
            # Clean up temp file
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink()
                
        except Exception as e:
            safe_print(f"[BULK_UPLOAD] Error processing {card.get('card_name', 'unknown')}: {e}")
            results.append({
                "success": False,
                "card_name": card.get("card_name", "Unknown"),
                "error": str(e)
            })
    
    return JSONResponse(results)
