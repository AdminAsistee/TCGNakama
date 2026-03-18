"""Direct test of bulk upload endpoint"""
import httpx
import asyncio
import hashlib
import os

async def test():
    # Create valid admin session cookie
    stored_email = os.getenv("ADMIN_EMAIL", "admin@tcgnakama.com")
    SESSION_SECRET = "your-secret-key-here-change-in-production"
    session_token = hashlib.sha256(f"{stored_email}{SESSION_SECRET}".encode()).hexdigest()[:32]
    
    cookies = {"admin_session": session_token}
    
    async with httpx.AsyncClient(cookies=cookies, follow_redirects=False) as client:
        print("Testing GET /admin/bulk-upload with valid session...")
        try:
            response = await client.get("http://localhost:8001/admin/bulk-upload", timeout=10.0)
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 500:
                print("\n=== 500 ERROR - FULL RESPONSE ===")
                print(response.text)
            elif response.status_code == 200:
                print("\n✓ SUCCESS! Page loaded")
                print(f"Response length: {len(response.text)} bytes")
            else:
                print(f"\nUnexpected status: {response.status_code}")
                print(response.text[:500])
                
        except Exception as e:
            print(f"\nException: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test())
