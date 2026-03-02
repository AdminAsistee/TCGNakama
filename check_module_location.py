"""
Check which admin.py file the server is actually loading
"""
import sys
from app.routers import admin

print("=" * 70)
print("MODULE LOCATION CHECK")
print("=" * 70)

print(f"\nadmin module file: {admin.__file__}")
print(f"admin router: {admin.router}")
print(f"Routes in admin router: {len(admin.router.routes)}")

# Check sys.path
print(f"\nPython sys.path:")
for i, path in enumerate(sys.path[:5]):
    print(f"  [{i}] {path}")

# Try to find the bulk_upload_page function
if hasattr(admin, 'bulk_upload_page'):
    print(f"\nbulk_upload_page function: {admin.bulk_upload_page}")
    print(f"  Location: {admin.bulk_upload_page.__code__.co_filename}")
    print(f"  Line: {admin.bulk_upload_page.__code__.co_firstlineno}")
else:
    print("\nWARNING: bulk_upload_page function NOT FOUND in admin module!")
    
# List all functions in admin module that contain 'bulk'
print(f"\nFunctions in admin module containing 'bulk':")
for name in dir(admin):
    if 'bulk' in name.lower():
        print(f"  - {name}")
