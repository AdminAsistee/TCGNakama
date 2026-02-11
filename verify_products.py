import requests

def verify_live_products():
    try:
        url = "http://127.0.0.1:8001"
        response = requests.get(url, timeout=10)
        content = response.text
        
        # Products from Shopify seen in test_shopify.py
        target_products = ["Shanks", "Zoro", "Luffy", "SV-P Promo"]
        
        print(f"--- Homepage Content Verification ---")
        found_any = False
        for p in target_products:
            if p.lower() in content.lower():
                print(f"SUCCESS: Found live product '{p}' on homepage.")
                found_any = True
            else:
                print(f"MISSING: Product '{p}' not found.")
        
        if not found_any:
            print("FAILURE: No live Shopify products found. Server may be in mock fallback mode.")
            
        # Check for mock products to confirm if it IS in mock mode
        mock_products = ["Charizard 1st Ed.", "Umbreon VMAX", "Lugia Holo"]
        print(f"\n--- Mock Content Check ---")
        for p in mock_products:
            if p.lower() in content.lower():
                print(f"INFO: Mock product '{p}' is present.")
            else:
                print(f"INFO: Mock product '{p}' is NOT present.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_live_products()
