"""Test if bulk upload page loads with collections"""
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(follow_redirects=False) as client:
        print("Testing bulk upload page with collections...")
        response = await client.get("http://localhost:8001/admin/bulk-upload")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Page loaded successfully!")
        elif response.status_code == 302:
            print(f"→ Redirected to: {response.headers.get('location')}")
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text[:500])

asyncio.run(test())
