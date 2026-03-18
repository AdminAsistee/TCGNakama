"""Test bulk upload endpoint directly"""
import httpx
import asyncio

async def test_endpoint():
    try:
        async with httpx.AsyncClient() as client:
            # Try to access the bulk upload page
            response = await client.get("http://localhost:8001/admin/bulk-upload", follow_redirects=True)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 500:
                print("Internal Server Error!")
                print(f"Response text (first 1000 chars):")
                print(response.text[:1000])
            elif response.status_code == 200:
                print("Success! Page loaded")
            else:
                print(f"Other status: {response.status_code}")
                print(response.text[:200])
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_endpoint())
