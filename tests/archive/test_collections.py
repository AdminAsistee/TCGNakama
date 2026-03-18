import asyncio
import os
from dotenv import load_dotenv
from app.dependencies import get_shopify_client

async def test_collections():
    load_dotenv()
    
    client = get_shopify_client()
    try:
        print("Fetching collections...")
        collections = await client.get_collections(first=10)
        
        print(f"Found {len(collections)} collections:")
        for collection in collections:
            print(f"- {collection['title']} (Handle: {collection['handle']}, ID: {collection['id']})")
            if collection['image']:
                print(f"  Image: {collection['image']}")
            else:
                print("  No image")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the client session if needed
        s_client = client.get_client()
        await s_client.aclose()

if __name__ == "__main__":
    asyncio.run(test_collections())
