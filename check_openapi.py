"""
Check if the running server has the bulk-upload route
"""
import requests

response = requests.get("http://localhost:8001/openapi.json")
openapi_spec = response.json()

print("=" * 70)
print("CHECKING OPENAPI SPEC FROM RUNNING SERVER")
print("=" * 70)

# Find all paths with 'bulk' in them
bulk_paths = {path: methods for path, methods in openapi_spec['paths'].items() if 'bulk' in path.lower()}

print(f"\nBulk-related paths in OpenAPI spec: {len(bulk_paths)}")
for path, methods in bulk_paths.items():
    print(f"\n{path}:")
    for method, details in methods.items():
        print(f"  {method.upper()}: {details.get('summary', 'No summary')}")

# Also check total admin paths
admin_paths = {path: methods for path, methods in openapi_spec['paths'].items() if '/admin' in path}
print(f"\nTotal admin paths: {len(admin_paths)}")

# List first 10 admin paths
print("\nFirst 10 admin paths:")
for i, path in enumerate(list(admin_paths.keys())[:10]):
    print(f"  {path}")
