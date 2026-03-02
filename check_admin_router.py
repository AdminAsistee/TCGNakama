"""
Check if admin router has the bulk-upload routes
"""
from app.routers import admin

print("=" * 70)
print("CHECKING ADMIN ROUTER DIRECTLY")
print("=" * 70)

# Get all routes from the admin router
routes = admin.router.routes

print(f"\nTotal routes in admin router: {len(routes)}")

# Find bulk-upload routes
bulk_routes = [r for r in routes if hasattr(r, 'path') and 'bulk' in str(r.path).lower()]

print(f"Bulk-upload routes in admin router: {len(bulk_routes)}")

for route in bulk_routes:
    print(f"\n  Path: {route.path}")
    print(f"  Name: {route.name if hasattr(route, 'name') else 'N/A'}")
    print(f"  Methods: {route.methods if hasattr(route, 'methods') else 'N/A'}")

# List all admin router routes
print("\n" + "=" * 70)
print("ALL ADMIN ROUTER ROUTES:")
print("=" * 70)

for route in routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        methods = list(route.methods)[0] if route.methods else 'N/A'
        print(f"{methods:6} {route.path}")
