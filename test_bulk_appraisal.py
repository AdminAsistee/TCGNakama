"""
Test script for bulk upload appraisal endpoint.
Tests the /admin/bulk-upload/appraise endpoint with a sample image.
"""

import httpx
import asyncio
from pathlib import Path


async def test_bulk_appraisal():
    """Test the bulk upload appraisal endpoint."""
    
    # Use the logo as a test image (not a real card, but tests the endpoint)
    test_image_path = Path("app/static/logo.png")
    
    if not test_image_path.exists():
        print(f"[X] Test image not found: {test_image_path}")
        return
    
    print(f"[OK] Found test image: {test_image_path}")
    
    # Prepare the multipart form data
    with open(test_image_path, "rb") as f:
        files = {
            "images": ("test_card.png", f, "image/png")
        }
        
        # Make request to appraisal endpoint
        url = "http://localhost:8001/admin/bulk-upload/appraise"
        
        print(f"\n[>>] Sending POST request to {url}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, files=files)
                
                print(f"\n[<<] Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("[OK] Appraisal endpoint is working!")
                    result = response.json()
                    print(f"\n[DATA] Response data:")
                    print(f"   Number of results: {len(result)}")
                    if result:
                        print(f"   First result: {result[0]}")
                elif response.status_code == 404:
                    print("[X] 404 Not Found - Endpoint not registered")
                    print("   This was the issue from the previous session.")
                elif response.status_code == 401 or response.status_code == 403:
                    print("[X] Authentication required")
                    print("   Need to be logged in as admin")
                else:
                    print(f"[X] Unexpected status code: {response.status_code}")
                    print(f"   Response: {response.text[:500]}")
                    
        except httpx.ConnectError:
            print("[X] Could not connect to server. Is it running on port 8001?")
        except Exception as e:
            print(f"[X] Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("BULK UPLOAD APPRAISAL ENDPOINT TEST")
    print("=" * 60)
    asyncio.run(test_bulk_appraisal())
    print("\n" + "=" * 60)
