import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.getcwd())

from app.dependencies import ShopifyClient

async def inspect_products():
    load_dotenv(override=True)
    client = ShopifyClient()
    
    print("Fetching sample products from Shopify...")
    try:
        products = await client.get_products()
        print(f"Total products fetched: {len(products)}")
        
        for i, p in enumerate(products[:10]):
            print(f"\n--- Product {i+1} ---")
            print(f"ID: {p['id']}")
            print(f"Title: {p['title']}")
            print(f"Set: {p['set']}")
            print(f"Number: {p['card_number']}")
            print(f"Tags: {p['tags']}")
            # print(f"Description: {p.get('description', '')[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_products())
