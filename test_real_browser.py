"""
Final diagnostic: Simulate real browser access to bulk-upload page
"""
import requests

BASE_URL = "http://localhost:8001"

print("=" * 70)
print("DIAGNOSTIC: Real Browser Simulation")
print("=" * 70)

# Create a session (like a browser)
session = requests.Session()

# Step 1: Login
print("\n[1] Logging in...")
login_data = {
    "email": "admin@tcgnakama.com",
    "password": "nakama2026"
}

login_response = session.post(
    f"{BASE_URL}/admin/login",
    data=login_data,
    allow_redirects=True
)

print(f"    Status: {login_response.status_code}")
print(f"    Final URL: {login_response.url}")
print(f"    Cookies: {dict(session.cookies)}")

# Step 2: Access bulk-upload
print("\n[2] Accessing /admin/bulk-upload...")
bulk_response = session.get(
    f"{BASE_URL}/admin/bulk-upload",
    allow_redirects=False
)

print(f"    Status: {bulk_response.status_code}")
print(f"    Headers: {dict(bulk_response.headers)}")

if bulk_response.status_code == 200:
    print("\n✓ SUCCESS! Page loaded correctly")
    print(f"    Content-Type: {bulk_response.headers.get('content-type')}")
    print(f"    Content Length: {len(bulk_response.text)} bytes")
    
    # Verify it's the right page
    if "Bulk Card Upload" in bulk_response.text:
        print("    ✓ Correct page title found")
    if "dropzone" in bulk_response.text:
        print("    ✓ Upload dropzone found")
    if "start-appraisal-btn" in bulk_response.text:
        print("    ✓ Appraisal button found")
        
elif bulk_response.status_code == 302:
    print(f"\n✗ REDIRECT: {bulk_response.headers.get('location')}")
    print("    This means authentication failed or session is invalid")
    
elif bulk_response.status_code == 404:
    print("\n✗ 404 NOT FOUND")
    print(f"    Response: {bulk_response.text}")
    
else:
    print(f"\n✗ UNEXPECTED STATUS: {bulk_response.status_code}")
    print(f"    Response: {bulk_response.text[:500]}")

print("\n" + "=" * 70)
