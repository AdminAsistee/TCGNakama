#!/usr/bin/env python3
"""Debug script to test bulk upload route directly"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("BULK UPLOAD ROUTE DEBUG")
print("=" * 60)

# Test 1: Import admin module
print("\n1. Testing admin module import...")
try:
    from app.routers import admin
    print("   [OK] Admin module imported successfully")
except Exception as e:
    print(f"   [ERROR] Failed to import: {e}")
    sys.exit(1)

# Test 2: Check routes
print("\n2. Checking routes in admin router...")
print(f"   Total routes: {len(admin.router.routes)}")

bulk_routes = [r for r in admin.router.routes if 'bulk' in str(r.path).lower()]
print(f"   Bulk upload routes found: {len(bulk_routes)}")
for r in bulk_routes:
    methods = r.methods if hasattr(r, 'methods') else 'N/A'
    print(f"     - {r.path} [{methods}]")

# Test 3: Check if function exists
print("\n3. Checking if bulk_upload_page function exists...")
if hasattr(admin, 'bulk_upload_page'):
    print("   ✓ bulk_upload_page function exists")
else:
    print("   ✗ bulk_upload_page function NOT found")

# Test 4: Check template file
print("\n4. Checking if template file exists...")
template_path = "app/templates/admin/bulk_upload.html"
if os.path.exists(template_path):
    print(f"   ✓ Template exists: {template_path}")
else:
    print(f"   ✗ Template NOT found: {template_path}")

# Test 5: Try to start app and list all routes
print("\n5. Testing FastAPI app routes...")
try:
    from app.main import app
    print(f"   Total app routes: {len(app.routes)}")
    
    # Find admin routes
    admin_routes = [r for r in app.routes if hasattr(r, 'path') and '/admin' in str(r.path)]
    print(f"   Admin routes: {len(admin_routes)}")
    
    # Check for bulk upload specifically
    bulk_in_app = [r for r in app.routes if hasattr(r, 'path') and 'bulk' in str(r.path).lower()]
    print(f"   Bulk upload in app routes: {len(bulk_in_app)}")
    for r in bulk_in_app:
        print(f"     - {r.path}")
        
except Exception as e:
    print(f"   ✗ Error loading app: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)
