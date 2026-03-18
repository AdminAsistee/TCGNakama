import httpx
import asyncio

async def test_cart_flow():
    base_url = "http://127.0.0.1:8001"
    variant_id = "gid://shopify/ProductVariant/50469962809591" # Pichaku
    
    print("--- 1. Adding to Cart ---")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{base_url}/cart/add?variant_id={variant_id}")
        print(f"Status: {resp.status_code}")
        print(f"Data: {resp.json()}")
        
        cookie = resp.cookies.get("cart_id")
        print(f"Cookie set: {cookie}")
        
        if not cookie:
             print("ERROR: No cart_id cookie returned!")
             return

        print("\n--- 2. Fetching Cart Drawer ---")
        # Ensure we send the cookie
        drawer_resp = await client.get(f"{base_url}/cart/drawer", cookies={"cart_id": cookie})
        print(f"Status: {drawer_resp.status_code}")
        
        if "Charizard" in drawer_resp.text:
             print("SUCCESS: Found mock item in drawer (from mock-cart)")
        elif "Pichaku" in drawer_resp.text:
             print("SUCCESS: Found Pichaku in drawer")
        else:
             print("FAILURE: Items list might be empty. Response snippet:")
             # Print lines around the empty state message
             lines = drawer_resp.text.split("\n")
             for i, line in enumerate(lines):
                  if "Your vault is empty" in line:
                       start = max(0, i-5)
                       end = min(len(lines), i+10)
                       print("\n".join(lines[start:end]))

if __name__ == "__main__":
    asyncio.run(test_cart_flow())
