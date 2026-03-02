"""
Test script to fetch a specific product from Shopify and see what the API returns.
"""
import asyncio
from app.dependencies import ShopifyClient
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_fetch_product():
    client = ShopifyClient()
    
    # The product ID from the dashboard
    product_id = "gid://shopify/Product/9905036820727"
    
    print(f"Attempting to fetch product: {product_id}")
    print("-" * 60)
    
    product = await client.get_product(product_id)
    
    if product:
        print("✅ Product found!")
        print(f"Title: {product.get('title')}")
        print(f"Price: {product.get('price')}")
        print(f"ID: {product.get('id')}")
        print(f"\nFull product data:")
        import json
        print(json.dumps(product, indent=2))
    else:
        print("❌ Product NOT found - get_product returned None")
        print("Check the server logs above for [DEBUG] and [ERROR] messages")

if __name__ == "__main__":
    asyncio.run(test_fetch_product())
