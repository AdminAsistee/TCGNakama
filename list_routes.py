"""List all registered routes in the app"""
import sys
sys.path.insert(0, r'c:\Users\amrca\Documents\antigravity\tcgnakama')

try:
    from app.main import app
    
    print("=== Registered Routes ===")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ','.join(route.methods) if route.methods else 'N/A'
            print(f"{methods:10} {route.path}")
            
    print("\n=== Looking for bulk-upload routes ===")
    bulk_routes = [r for r in app.routes if hasattr(r, 'path') and 'bulk-upload' in r.path]
    if bulk_routes:
        for route in bulk_routes:
            print(f"Found: {route.path}")
            if hasattr(route, 'endpoint'):
                print(f"  Endpoint: {route.endpoint.__name__}")
    else:
        print("NO bulk-upload routes found!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
