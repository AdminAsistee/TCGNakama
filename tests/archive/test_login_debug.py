"""
Test login with debug output
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8001"

print("=" * 70)
print("LOGIN DEBUG TEST")
print("=" * 70)

# Check environment variables
admin_email = os.getenv("ADMIN_EMAIL", "admin@tcgnakama.com")
admin_password = os.getenv("ADMIN_PASSWORD", "nakama2026")

print(f"\nExpected credentials:")
print(f"  Email: {admin_email}")
print(f"  Password: {admin_password}")

# Test with these credentials
session = requests.Session()

login_data = {
    "email": admin_email,
    "password": admin_password
}

print(f"\nSending login request...")
print(f"  URL: {BASE_URL}/admin/login")
print(f"  Data: {login_data}")

response = session.post(
    f"{BASE_URL}/admin/login",
    data=login_data,
    allow_redirects=False  # Don't follow redirects
)

print(f"\nResponse:")
print(f"  Status: {response.status_code}")
print(f"  Headers: {dict(response.headers)}")
print(f"  Cookies: {dict(response.cookies)}")

if response.status_code == 303:
    print(f"\n SUCCESS! Redirect to: {response.headers.get('location')}")
    print(f"  Session cookie: {response.cookies.get('admin_session')}")
    
    # Now try accessing bulk-upload
    print(f"\nTesting bulk-upload access...")
    bulk_response = session.get(f"{BASE_URL}/admin/bulk-upload")
    print(f"  Status: {bulk_response.status_code}")
    if bulk_response.status_code == 200:
        print(f"   SUCCESS! Bulk upload page loaded")
        if "Bulk Card Upload" in bulk_response.text:
            print(f"   Correct page content verified")
    else:
        print(f"   FAILED: {bulk_response.status_code}")
        
elif response.status_code == 200:
    print(f"\n FAILED! Returned login page (credentials rejected)")
    if "Invalid email or password" in response.text:
        print(f"  Error message found in response")
else:
    print(f"\n UNEXPECTED: {response.status_code}")
    print(f"  Body: {response.text[:500]}")
