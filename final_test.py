"""
Final test: Try accessing the route directly, bypassing OpenAPI
"""
import requests

BASE_URL = "http://localhost:8001"
session = requests.Session()

# Login
login_response = session.post(
    f"{BASE_URL}/admin/login",
    data={"email": "admin@asistee.com", "password": "nakama2026"},
    allow_redirects=False
)

print("=" * 70)
print("FINAL DIRECT ACCESS TEST")
print("=" * 70)

print(f"\n[1] Login: {login_response.status_code}")
print(f"    Cookie set: {'admin_session' in session.cookies}")

# Try accessing bulk-upload
print(f"\n[2] Accessing /admin/bulk-upload...")
response = session.get(f"{BASE_URL}/admin/bulk-upload", allow_redirects=False)

print(f"    Status: {response.status_code}")
print(f"    Content-Type: {response.headers.get('content-type', 'N/A')}")

if response.status_code == 200:
    print("\n    *** SUCCESS! ***")
    print(f"    Content length: {len(response.text)} bytes")
    
    # Check for key elements
    checks = [
        ("Bulk Card Upload", "Page title"),
        ("dropzone", "Upload dropzone"),
        ("start-appraisal-btn", "Appraisal button"),
        ("preview-grid", "Preview grid"),
    ]
    
    print("\n    Content verification:")
    for text, desc in checks:
        found = text in response.text
        status = "[OK]" if found else "[MISSING]"
        print(f"      {status} {desc}")
        
elif response.status_code == 404:
    print(f"\n    *** FAILED: 404 Not Found ***")
    print(f"    Response: {response.text}")
else:
    print(f"\n    *** Unexpected status: {response.status_code} ***")
    print(f"    Response: {response.text[:200]}")

print("\n" + "=" * 70)
