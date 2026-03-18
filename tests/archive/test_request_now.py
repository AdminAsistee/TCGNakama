"""Make a request and check server logs"""
import httpx
import hashlib

# Create valid session
SESSION_SECRET = "your-secret-key-here-change-in-production"
stored_email = "admin@tcgnakama.com"
session_token = hashlib.sha256(f"{stored_email}{SESSION_SECRET}".encode()).hexdigest()[:32]

print(f"Session token: {session_token}")
print("Making request to /admin/bulk-upload...")

response = httpx.get(
    "http://localhost:8001/admin/bulk-upload",
    cookies={"admin_session": session_token},
    follow_redirects=False,
    timeout=10.0
)

print(f"\nStatus: {response.status_code}")
print(f"Headers: {dict(response.headers)}")

if response.status_code == 500:
    print("\n=== 500 ERROR RESPONSE ===")
    print(response.text)
elif response.status_code == 200:
    print(f"\n✓ SUCCESS! Response length: {len(response.text)} bytes")
else:
    print(f"\nResponse: {response.text[:500]}")
