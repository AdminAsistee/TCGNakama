"""
Test on port 8001 after cleanup
"""
import requests

BASE_URL = "http://localhost:8001"
session = requests.Session()

print("=" * 70)
print("TESTING ON PORT 8001 (AFTER CLEANUP)")
print("=" * 70)

# Login
print("\n[1] Logging in...")
login_response = session.post(
    f"{BASE_URL}/admin/login",
    data={"email": "admin@asistee.com", "password": "nakama2026"},
    allow_redirects=False
)

print(f"    Status: {login_response.status_code}")
print(f"    Cookie: {'admin_session' in session.cookies}")

# Try accessing bulk-upload
print("\n[2] Accessing /admin/bulk-upload...")
response = session.get(f"{BASE_URL}/admin/bulk-upload", allow_redirects=False)

print(f"    Status: {response.status_code}")
print(f"    Content-Type: {response.headers.get('content-type', 'N/A')}")

if response.status_code == 200:
    print("\n    *** SUCCESS! PORT 8001 NOW WORKS! ***")
    print(f"    Content length: {len(response.text)} bytes")
    
    # Verify content
    if "Bulk Card Upload" in response.text:
        print("    [OK] Page title found")
    if "dropzone" in response.text:
        print("    [OK] Upload dropzone found")
        
    print(f"\n    You can now use port 8001:")
    print(f"    http://localhost:8001/admin/bulk-upload")
        
elif response.status_code == 404:
    print(f"\n    Still 404 - may need manual intervention")
else:
    print(f"\n    Status: {response.status_code}")

print("\n" + "=" * 70)
