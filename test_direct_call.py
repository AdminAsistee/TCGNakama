"""
Test calling the bulk_upload_page function directly
"""
from app.routers.admin import bulk_upload_page
from fastapi import Request
from fastapi.testclient import TestClient
from app.main import app
import asyncio

print("=" * 70)
print("DIRECT FUNCTION TEST")
print("=" * 70)

# Test 1: Try calling the function directly
print("\n[1] Testing if function can be called directly...")
try:
    # Create a mock request
    client = TestClient(app)
    
    # Login first to get a valid session
    login_response = client.post("/admin/login", data={
        "email": "admin@asistee.com",
        "password": "nakama2026"
    }, follow_redirects=False)
    
    print(f"    Login status: {login_response.status_code}")
    
    # Now try to access the route through TestClient
    response = client.get("/admin/bulk-upload", cookies=login_response.cookies)
    print(f"    Bulk upload status: {response.status_code}")
    
    if response.status_code == 200:
        print("    SUCCESS via TestClient!")
        print(f"    Content type: {response.headers.get('content-type')}")
        if "Bulk Card Upload" in response.text:
            print("    Page content verified!")
    else:
        print(f"    FAILED: {response.text[:200]}")
        
except Exception as e:
    print(f"    ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Check if there's a middleware or dependency issue
print("\n[2] Checking route registration order...")
from app.main import app

routes_before_bulk = []
bulk_route_index = None

for i, route in enumerate(app.routes):
    if hasattr(route, 'path'):
        if route.path == '/admin/bulk-upload':
            bulk_route_index = i
            break
        if '/admin' in route.path:
            routes_before_bulk.append((i, route.path))

if bulk_route_index:
    print(f"    Bulk-upload route is at index: {bulk_route_index}")
    print(f"    Admin routes before it: {len(routes_before_bulk)}")
    
    # Check if there's a catch-all route before it
    for idx, path in routes_before_bulk:
        if '{' in path or '*' in path:
            print(f"    WARNING: Catch-all route at index {idx}: {path}")
