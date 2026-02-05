import httpx
import asyncio

async def test():
    base_url = "http://127.0.0.1:8001"
    v1 = "gid://shopify/ProductVariant/50469962809591" # Pichaku
    v2 = "gid://shopify/ProductVariant/50470095421687" # Raichu
    
    async with httpx.AsyncClient() as client:
        # 1. Add v1 with Qty 2
        print("Adding Pichaku Qty 2...")
        r1 = await client.post(f"{base_url}/cart/add?variant_id={v1}&quantity=2")
        print(f"R1: {r1.json()}")
        
        # 2. Add v2 with Qty 5
        print("\nAdding Raichu Qty 5...")
        r2 = await client.post(f"{base_url}/cart/add?variant_id={v2}&quantity=5", cookies=r1.cookies)
        print(f"R2: {r2.json()}")
        
        # 3. Check Drawer
        print("\nFetching Drawer...")
        r3 = await client.get(f"{base_url}/cart/drawer", cookies=r2.cookies)
        content = r3.text
        
        # Look for quantities in the html
        import re
        qtys = re.findall(r'text-white">(\d+)</span>', content)
        print(f"Quantities found in drawer: {qtys}")
        
        total_q = r2.json().get("total_quantity")
        print(f"Total Quantity reported in JSON: {total_q}")

if __name__ == "__main__":
    asyncio.run(test())
