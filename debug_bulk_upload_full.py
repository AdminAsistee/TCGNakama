"""
Comprehensive debug script for bulk upload functionality.
Tests the entire flow: login -> appraise -> confirm
"""
import asyncio
import httpx
import json
from pathlib import Path

async def debug_bulk_upload():
    base_url = "http://localhost:8001"
    
    print("=" * 80)
    print("BULK UPLOAD DEBUG SCRIPT")
    print("=" * 80)
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        # Step 1: Login
        print("\n[STEP 1] Logging in...")
        login_response = await client.post(
            f"{base_url}/admin/login",
            data={
                "email": "admin@asistee.com",
                "password": "nakama2026"
            }
        )
        print(f"Login Status: {login_response.status_code}")
        
        if login_response.status_code != 200:
            print(f"[ERROR] Login failed!")
            print(f"Response: {login_response.text[:500]}")
            return
        
        print("[OK] Login successful")
        
        # Step 2: Test with mock card data (simulating what frontend sends)
        print("\n[STEP 2] Testing bulk confirm with mock data...")
        
        mock_card = {
            "card_name": "テンペローグ (TEMPERO-LOGUE) - OP10 #OP10-046",
            "card_name_japanese": "テンペローグ",
            "card_name_english": "TEMPERO-LOGUE",
            "set_name": "OP10",
            "card_number": "OP10-046",
            "rarity": "Ultra Rare",
            "vendor": "Bandai",
            "price": 100,
            "exists": False,
            "quantity": 1,
            "temp_path": "",
            "image_url": "",
            "year": "2024",
            "manufacturer": "Bandai",
            "shopify_product_id": None,
            "shopify_variant_id": None,
            "shopify_inventory_item_id": None,
            "current_quantity": 0
        }
        
        print("\n[DATA] Sending card data:")
        print(json.dumps(mock_card, indent=2, ensure_ascii=False))
        
        # Step 3: Send to confirm endpoint
        print("\n[STEP 3] Posting to /admin/bulk-upload/confirm...")
        
        try:
            confirm_response = await client.post(
                f"{base_url}/admin/bulk-upload/confirm",
                json={"cards": [mock_card]},
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n[RESPONSE] Status: {confirm_response.status_code}")
            print(f"Response Headers: {dict(confirm_response.headers)}")
            
            if confirm_response.status_code == 200:
                try:
                    result_data = confirm_response.json()
                    print("\n[OK] SUCCESS! Response data:")
                    print(json.dumps(result_data, indent=2, ensure_ascii=False))
                    
                    # Check if product was created
                    if result_data and len(result_data) > 0:
                        first_result = result_data[0]
                        if first_result.get("success"):
                            print(f"\n[SUCCESS] Product created successfully!")
                            print(f"Product ID: {first_result.get('product_id')}")
                            print(f"Card Name: {first_result.get('card_name')}")
                        else:
                            print(f"\n[ERROR] Product creation failed!")
                            print(f"Error: {first_result.get('error')}")
                    else:
                        print("\n[WARNING] Empty response array")
                        
                except json.JSONDecodeError as e:
                    print(f"\n[ERROR] Failed to parse JSON response: {e}")
                    print(f"Raw response: {confirm_response.text[:1000]}")
            else:
                print(f"\n[ERROR] Request failed with status {confirm_response.status_code}")
                print(f"Response body: {confirm_response.text[:1000]}")
                
        except Exception as e:
            print(f"\n[ERROR] Exception occurred: {e}")
            import traceback
            print(traceback.format_exc())
        
        print("\n" + "=" * 80)
        print("DEBUG COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_bulk_upload())
