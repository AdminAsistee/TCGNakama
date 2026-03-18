"""Test bulk upload with authentication"""
import httpx
import asyncio

async def test_with_auth():
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # First, try to login
            print("1. Testing login...")
            login_response = await client.post(
                "http://localhost:8001/admin/login",
                data={"username": "admin", "password": "admin123"}
            )
            print(f"   Login status: {login_response.status_code}")
            
            # Now try bulk upload
            print("2. Testing bulk upload page...")
            response = await client.get("http://localhost:8001/admin/bulk-upload")
            print(f"   Bulk upload status: {response.status_code}")
            
            if response.status_code == 500:
                print("\n[ERROR] Internal Server Error!")
                print("Response text:")
                print(response.text[:2000])
            elif response.status_code == 200:
                print("\n[SUCCESS] Page loaded!")
            else:
                print(f"\n[INFO] Status {response.status_code}")
                print(response.text[:500])
                
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_with_auth())
