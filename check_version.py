"""
Check if there's a version mismatch between the file and what's loaded
"""
import importlib
import sys

# Force reload of the admin module
if 'app.routers.admin' in sys.modules:
    del sys.modules['app.routers.admin']
if 'app.routers' in sys.modules:
    del sys.modules['app.routers']

# Import fresh
from app.routers import admin
from app.main import app

print("=" * 70)
print("VERSION CHECK")
print("=" * 70)

# Check admin router
admin_routes = [r for r in admin.router.routes if hasattr(r, 'path')]
bulk_in_admin = [r for r in admin_routes if 'bulk' in str(r.path).lower()]

print(f"\nAdmin Router Module:")
print(f"  Total routes: {len(admin_routes)}")
print(f"  Bulk routes: {len(bulk_in_admin)}")
for r in bulk_in_admin:
    print(f"    - {r.path}")

# Check main app
app_routes = [r for r in app.routes if hasattr(r, 'path')]
bulk_in_app = [r for r in app_routes if 'bulk' in str(r.path).lower()]

print(f"\nMain App:")
print(f"  Total routes: {len(app_routes)}")
print(f"  Bulk routes: {len(bulk_in_app)}")
for r in bulk_in_app:
    print(f"    - {r.path}")

# Check if admin router is included
admin_prefix_routes = [r for r in app_routes if hasattr(r, 'path') and '/admin' in str(r.path)]
print(f"\nAdmin-prefixed routes in app: {len(admin_prefix_routes)}")

# Check the file modification time
import os
from datetime import datetime

admin_file = "app/routers/admin.py"
if os.path.exists(admin_file):
    mtime = os.path.getmtime(admin_file)
    mod_time = datetime.fromtimestamp(mtime)
    print(f"\nFile: {admin_file}")
    print(f"  Last modified: {mod_time}")
    print(f"  File size: {os.path.getsize(admin_file)} bytes")
