"""
Inspect raw PriceCharting API response to find set name field
"""
import asyncio
import httpx
import json
from urllib.parse import quote_plus

API_KEY = "40d8d65da33130a111830698dac61dfe04099357"

async def inspect_response():
    url = f"https://www.pricecharting.com/api/products?t={API_KEY}&q={quote_plus('Sabo ST13 ST13-007')}"
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        data = response.json()
        products = data.get('products', [])
        
        print(f"Found {len(products)} products\n")
        for p in products:
            print(f"Product name: {p.get('product-name')}")
            print(f"  All keys: {list(p.keys())}")
            # Print all non-empty fields
            for k, v in p.items():
                if v and k != 'id':
                    print(f"  {k}: {v}")
            print()

if __name__ == "__main__":
    asyncio.run(inspect_response())
