"""Test bulk upload page with session"""
import httpx
import asyncio

async def test():
    # Create a session cookie to bypass auth
    cookies = {"session": "test_session"}
    
    async with httpx.AsyncClient(cookies=cookies, follow_redirects=False) as client:
        print("Testing GET /admin/bulk-upload...")
        try:
            response = await client.get("http://localhost:8001/admin/bulk-upload")
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 500:
                print("\n=== 500 ERROR RESPONSE ===")
                print(response.text[:2000])
            elif response.status_code == 200:
                print("\n✓ Page loaded successfully!")
                print(f"Response length: {len(response.text)} bytes")
            else:
                print(f"\nResponse: {response.text[:500]}")
                
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test())
