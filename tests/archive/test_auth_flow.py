from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test with follow_redirects=True to see the full flow
print("=" * 50)
print("TEST: Full login flow with redirects")
print("=" * 50)

# Step 1: Login
login_response = client.post(
    "/admin/login",
    data={
        "email": "admin@tcgnakama.com",
        "password": "nakama2026"
    },
    follow_redirects=True
)

print(f"Final Status: {login_response.status_code}")
print(f"Final URL: {login_response.url}")
print(f"Cookies: {dict(login_response.cookies)}")
print(f"Content Type: {login_response.headers.get('content-type')}")
print(f"Content Preview: {login_response.text[:300]}")

# Step 2: Now try bulk-upload with the session
print("\n" + "=" * 50)
print("TEST: Access bulk-upload with session cookies")
print("=" * 50)

bulk_response = client.get(
    "/admin/bulk-upload",
    cookies=login_response.cookies,
    follow_redirects=False
)

print(f"Status: {bulk_response.status_code}")
print(f"Headers: {dict(bulk_response.headers)}")
if bulk_response.status_code == 200:
    print("✓ SUCCESS! Bulk upload page loaded")
    print(f"Content length: {len(bulk_response.text)}")
    # Check if it's the right template
    if "Bulk Card Upload" in bulk_response.text:
        print("✓ Correct template loaded!")
else:
    print(f"✗ FAILED: {bulk_response.text[:500]}")
