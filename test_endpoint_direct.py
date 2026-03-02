"""Test the exact endpoint with detailed error capture"""
import asyncio
import hashlib
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, 'app')

# Import the app
from main import app

# Create test client
client = TestClient(app)

# Create valid session
SESSION_SECRET = "your-secret-key-here-change-in-production"
stored_email = "admin@tcgnakama.com"
session_token = hashlib.sha256(f"{stored_email}{SESSION_SECRET}".encode()).hexdigest()[:32]

print("Testing /admin/bulk-upload endpoint...")
print(f"Session token: {session_token}\n")

try:
    response = client.get(
        "/admin/bulk-upload",
        cookies={"admin_session": session_token},
        follow_redirects=False
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 500:
        print("\n=== 500 INTERNAL SERVER ERROR ===")
        print(response.text)
    elif response.status_code == 200:
        print(f"\n✓ SUCCESS! Page loaded ({len(response.text)} bytes)")
    else:
        print(f"\nResponse: {response.text[:500]}")
        
except Exception as e:
    print(f"\nEXCEPTION: {e}")
    import traceback
    traceback.print_exc()
