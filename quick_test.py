"""Direct test to trigger the endpoint"""
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(follow_redirects=False) as client:
        print("Requesting /admin/bulk-upload...")
        response = await client.get("http://localhost:8001/admin/bulk-upload")
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        if response.status_code >= 400:
            print(f"Error response:\n{response.text[:500]}")

asyncio.run(test())
