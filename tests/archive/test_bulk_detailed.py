"""Test with proper session/cookies to simulate browser access"""
import httpx
import asyncio

async def test_with_session():
    try:
        # Use a session to maintain cookies
        async with httpx.AsyncClient(follow_redirects=True) as client:
            print("Testing bulk upload endpoint...")
            response = await client.get("http://localhost:8001/admin/bulk-upload")
            
            print(f"Status: {response.status_code}")
            print(f"URL: {response.url}")
            
            if response.status_code == 500:
                print("\n=== ERROR RESPONSE ===")
                print(response.text)
            elif response.status_code == 200:
                print("\n=== SUCCESS ===")
                # Check if collections variable is in the response
                if "availableCollections" in response.text:
                    print("✓ availableCollections found in response")
                    # Extract the line with availableCollections
                    for line in response.text.split('\n'):
                        if 'availableCollections' in line:
                            print(f"Line: {line.strip()[:200]}")
                            break
                else:
                    print("✗ availableCollections NOT found")
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_with_session())
