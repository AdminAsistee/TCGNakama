import asyncio
import os
from dotenv import load_dotenv
from app.dependencies import get_shopify_client

async def test_collection_products():
    load_dotenv()
    
    client = get_shopify_client()
    handle = "pokemon" # Known handle from previous test
    
    try:
        print(f"Fetching products for collection: {handle}...")
        products = await client.get_collection_products(handle=handle, first=10)
        
        print(f"Found {len(products)} products in collection '{handle}':")
        for product in products:
            print(f"- {product['title']} (ID: {product['id']}, Price: {product['price']})")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the client session
        s_client = client.get_client()
        await s_client.aclose()

if __name__ == "__main__":
    asyncio.run(test_collection_products())
