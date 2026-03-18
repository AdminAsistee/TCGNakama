"""
Test on port 8000
"""
import requests

BASE_URL = "http://localhost:8000"
session = requests.Session()

print("=" * 70)
print("TESTING ON PORT 8000")
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
    print("\n    *** SUCCESS! THE BULK UPLOAD PAGE WORKS! ***")
    print(f"    Content length: {len(response.text)} bytes")
    
    # Verify content
    if "Bulk Card Upload" in response.text:
        print("    [OK] Page title found")
    if "dropzone" in response.text:
        print("    [OK] Upload dropzone found")
    if "start-appraisal-btn" in response.text:
        print("    [OK] Appraisal button found")
        
    print(f"\n    You can now access the bulk upload page at:")
    print(f"    http://localhost:8000/admin/bulk-upload")
        
elif response.status_code == 404:
    print(f"\n    FAILED: 404 Not Found")
    print(f"    Response: {response.text}")
else:
    print(f"\n    Status: {response.status_code}")
    print(f"    Response: {response.text[:200]}")

print("\n" + "=" * 70)
