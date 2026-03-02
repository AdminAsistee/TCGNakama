"""Test bulk upload page access"""
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(follow_redirects=True, cookies={"admin_token": "test"}) as client:
        print("Testing bulk upload page...")
        try:
            response = await client.get("http://localhost:8001/admin/bulk-upload")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✓ Page loaded successfully!")
            else:
                print(f"✗ Error: {response.status_code}")
                print(response.text[:1000])
        except Exception as e:
            print(f"Exception: {e}")

asyncio.run(test())
