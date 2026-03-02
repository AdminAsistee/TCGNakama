"""
Test script to directly test inventory increment functionality
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Import the ShopifyClient
import sys
sys.path.insert(0, 'app')
from dependencies import ShopifyClient

async def test_increment():
    client = ShopifyClient()
    admin_token = os.getenv("SHOPIFY_ADMIN_TOKEN")
    
    # Use a known inventory item ID from your Shopify store
    # You'll need to replace this with an actual inventory item ID
    test_inventory_item_id = "gid://shopify/InventoryItem/52515118853"  # Example from logs
    
    print("=" * 70)
    print("TESTING INVENTORY INCREMENT")
    print("=" * 70)
    print(f"Admin Token: {admin_token[:20]}...")
    print(f"Inventory Item ID: {test_inventory_item_id}")
    print()
    
    # Test incrementing by 1
    print("Attempting to increment inventory by 1...")
    try:
        await client._increment_inventory(admin_token, test_inventory_item_id, 1)
        print("✓ Increment completed successfully")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_increment())
