"""Trigger bulk upload page and capture error"""
import httpx
import time

# Wait a moment for server to be ready
time.sleep(1)

# Make request
response = httpx.get("http://localhost:8001/admin/bulk-upload", follow_redirects=False, timeout=5.0)
print(f"Status: {response.status_code}")
if response.status_code == 500:
    print("GOT 500 ERROR")
    print(response.text[:1000])
elif response.status_code == 302:
    print(f"Redirect to: {response.headers.get('location')}")
else:
    print(f"Success! Length: {len(response.text)}")
