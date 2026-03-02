"""Test collections fetching"""
import sys
sys.path.insert(0, r'c:\Users\amrca\Documents\antigravity\tcgnakama')

import asyncio
from app.dependencies import ShopifyClient

async def test():
    client = ShopifyClient()
    
    # Test with admin token (simulating what bulk upload does)
    print("Testing get_collections with admin_token...")
    try:
        # Get admin token from session (we'll use None to test fallback)
        collections = await client.get_collections(admin_token=None)
        print(f"Collections returned: {collections}")
        print(f"Type: {type(collections)}")
        print(f"Length: {len(collections)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
