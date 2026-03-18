from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test 1: Check if route exists
print("=" * 50)
print("TEST 1: Checking all admin routes")
print("=" * 50)
admin_routes = [r for r in app.routes if hasattr(r, 'path') and '/admin' in str(r.path)]
for route in admin_routes:
    if hasattr(route, 'methods'):
        print(f"{list(route.methods)[0]:6} {route.path}")
    else:
        print(f"{'N/A':6} {route.path}")

# Test 2: Try accessing bulk-upload without auth
print("\n" + "=" * 50)
print("TEST 2: Accessing /admin/bulk-upload without auth")
print("=" * 50)
response = client.get("/admin/bulk-upload", follow_redirects=False)
print(f"Status Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
if response.status_code == 302:
    print(f"Redirect to: {response.headers.get('location')}")
else:
    print(f"Response: {response.text[:200]}")

# Test 3: Login and try with auth
print("\n" + "=" * 50)
print("TEST 3: Login and access with auth")
print("=" * 50)
login_response = client.post("/admin/login", data={
    "email": "admin@tcgnakama.com",
    "password": "nakama2026"
}, follow_redirects=False)
print(f"Login Status: {login_response.status_code}")
print(f"Login Headers: {dict(login_response.headers)}")

# Extract cookies
cookies = login_response.cookies

# Try accessing bulk-upload with auth
auth_response = client.get("/admin/bulk-upload", cookies=cookies, follow_redirects=False)
print(f"\nBulk Upload Status: {auth_response.status_code}")
if auth_response.status_code == 200:
    print("SUCCESS! Page loaded")
    print(f"Content length: {len(auth_response.text)}")
else:
    print(f"Response: {auth_response.text[:500]}")
