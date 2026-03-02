"""
Simple test to verify login works correctly.
"""

import httpx
import asyncio


async def test_login():
    """Test admin login."""
    
    async with httpx.AsyncClient(follow_redirects=False) as client:
        login_url = "http://localhost:8001/admin/login"
        
        # Try with form data (application/x-www-form-urlencoded)
        print("[>>] Testing login with form data...")
        login_data = {
            "email": "admin@asistee.com",
            "password": "nakama2026"
        }
        
        response = await client.post(login_url, data=login_data)
        print(f"[<<] Status: {response.status_code}")
        print(f"[<<] Headers: {dict(response.headers)}")
        
        if response.status_code == 303:
            print("[OK] Login successful!")
            print(f"[OK] Cookies: {response.cookies}")
            return True
        else:
            print(f"[X] Login failed")
            if "error" in response.text.lower():
                print("[X] Error message found in response")
            return False


if __name__ == "__main__":
    asyncio.run(test_login())
