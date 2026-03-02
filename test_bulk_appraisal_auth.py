"""
Test script for bulk upload appraisal endpoint with authentication.
Tests the /admin/bulk-upload/appraise endpoint with admin login.
"""

import httpx
import asyncio
from pathlib import Path


async def test_bulk_appraisal_with_auth():
    """Test the bulk upload appraisal endpoint with authentication."""
    
    # Use the logo as a test image (not a real card, but tests the endpoint)
    test_image_path = Path("app/static/logo.png")
    
    if not test_image_path.exists():
        print(f"[X] Test image not found: {test_image_path}")
        return
    
    print(f"[OK] Found test image: {test_image_path}")
    
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
        # Step 1: Login to get session cookie
        print("\n[>>] Logging in as admin...")
        login_url = "http://localhost:8001/admin/login"
        login_data = {
            "email": "admin@asistee.com",
            "password": "nakama2026"
        }
        
        login_response = await client.post(login_url, data=login_data)
        print(f"[<<] Login response: {login_response.status_code}")
        
        if login_response.status_code == 303:
            # Successful login - extract session cookie
            cookies = login_response.cookies
            print(f"[OK] Logged in successfully, got session cookie")
        elif login_response.status_code == 200:
            # Login form returned (likely wrong credentials)
            print(f"[X] Login failed - check credentials")
            print(f"   Response preview: {login_response.text[:200]}")
            return False
        else:
            print(f"[X] Unexpected login response: {login_response.status_code}")
            return False
        
        # Step 2: Test appraisal endpoint with session
        print(f"\n[>>] Testing appraisal endpoint...")
        
        with open(test_image_path, "rb") as f:
            files = {
                "images": ("test_card.png", f, "image/png")
            }
            
            url = "http://localhost:8001/admin/bulk-upload/appraise"
            
            try:
                response = await client.post(url, files=files, cookies=cookies)
                
                print(f"[<<] Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("[OK] Appraisal endpoint is working!")
                    result = response.json()
                    print(f"\n[DATA] Response data:")
                    print(f"   Number of results: {len(result)}")
                    if result:
                        print(f"\n   First result:")
                        for key, value in result[0].items():
                            if key != "temp_path":  # Skip long paths
                                print(f"      {key}: {value}")
                    return True
                elif response.status_code == 404:
                    print("[X] 404 Not Found - Endpoint not registered")
                    print("   This was the issue from the previous session.")
                    return False
                elif response.status_code == 302:
                    print("[X] Still getting redirected - authentication issue")
                    return False
                else:
                    print(f"[X] Unexpected status code: {response.status_code}")
                    print(f"   Response: {response.text[:500]}")
                    return False
                    
            except httpx.ConnectError:
                print("[X] Could not connect to server. Is it running on port 8001?")
                return False
            except Exception as e:
                print(f"[X] Error: {e}")
                import traceback
                traceback.print_exc()
                return False


if __name__ == "__main__":
    print("=" * 60)
    print("BULK UPLOAD APPRAISAL ENDPOINT TEST (WITH AUTH)")
    print("=" * 60)
    success = asyncio.run(test_bulk_appraisal_with_auth())
    print("\n" + "=" * 60)
    if success:
        print("RESULT: All tests passed!")
    else:
        print("RESULT: Some tests failed")
    print("=" * 60)
