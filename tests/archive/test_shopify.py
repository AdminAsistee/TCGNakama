import asyncio
import os
from dotenv import load_dotenv
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.dependencies import ShopifyClient

async def test_shopify():
    load_dotenv()
    client = ShopifyClient()
    print("Testing ShopifyClient.get_products()...")
    try:
        products = await client.get_products()
        print(f"Success! Found {len(products)} products.")
        if products:
            print(f"First product: {products[0]['title']}")
        else:
            print("Warning: No products returned.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_shopify())
