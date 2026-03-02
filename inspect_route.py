"""
Deep inspection of the bulk-upload route
"""
from app.main import app
from fastapi.routing import APIRoute

print("=" * 70)
print("ROUTE INSPECTION")
print("=" * 70)

# Find all routes
all_routes = []
for route in app.routes:
    if hasattr(route, 'path'):
        all_routes.append(route)

# Find bulk-upload routes
bulk_routes = [r for r in all_routes if 'bulk' in str(r.path).lower()]

print(f"\nFound {len(bulk_routes)} bulk-upload related routes:\n")

for route in bulk_routes:
    print(f"Path: {route.path}")
    print(f"  Name: {route.name if hasattr(route, 'name') else 'N/A'}")
    print(f"  Methods: {route.methods if hasattr(route, 'methods') else 'N/A'}")
    
    if isinstance(route, APIRoute):
        print(f"  Endpoint: {route.endpoint}")
        print(f"  Dependencies: {len(route.dependencies) if hasattr(route, 'dependencies') else 0}")
        
        # Check if endpoint function exists and is callable
        if callable(route.endpoint):
            print(f"  Endpoint callable: YES")
            print(f"  Endpoint name: {route.endpoint.__name__}")
        else:
            print(f"  Endpoint callable: NO - THIS IS THE PROBLEM!")
    print()

# Also check if there are any routes with similar paths
print("=" * 70)
print("ALL ADMIN ROUTES (for comparison):")
print("=" * 70)

admin_routes = [r for r in all_routes if '/admin' in str(r.path)]
for route in admin_routes[:15]:  # Show first 15
    methods = list(route.methods)[0] if hasattr(route, 'methods') else 'N/A'
    print(f"{methods:6} {route.path}")
