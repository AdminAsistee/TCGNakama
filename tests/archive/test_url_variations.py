"""
Test all variations of the bulk-upload URL
"""
import requests

BASE_URL = "http://localhost:8001"
session = requests.Session()

# Login first
login_response = session.post(
    f"{BASE_URL}/admin/login",
    data={"email": "admin@asistee.com", "password": "nakama2026"},
    allow_redirects=False
)

print(f"Login: {login_response.status_code}")
print(f"Cookie: {session.cookies.get('admin_session')}")

# Test different URL variations
urls = [
    "/admin/bulk-upload",
    "/admin/bulk-upload/",
    "/admin/bulk_upload",
    "/admin/bulkupload",
]

print("\n" + "=" * 70)
print("Testing URL variations:")
print("=" * 70)

for url in urls:
    response = session.get(f"{BASE_URL}{url}", allow_redirects=False)
    status_icon = "[OK]" if response.status_code == 200 else "[FAIL]"
    print(f"{status_icon} {url:30} -> {response.status_code}")
    
# Also test the routes that we know work
print("\n" + "=" * 70)
print("Testing known working routes:")
print("=" * 70)

working_routes = [
    "/admin",
    "/admin/analytics",
    "/admin/settings",
]

for url in working_routes:
    response = session.get(f"{BASE_URL}{url}", allow_redirects=False)
    status_icon = "[OK]" if response.status_code == 200 else "[FAIL]"
    print(f"{status_icon} {url:30} -> {response.status_code}")
