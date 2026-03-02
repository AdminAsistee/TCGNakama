from app.routers import admin

print('SUCCESS: admin module loaded')
print(f'Router has {len(admin.router.routes)} routes')

bulk_routes = [r for r in admin.router.routes if 'bulk' in str(r.path).lower()]
print(f'Bulk upload routes: {len(bulk_routes)}')
for r in bulk_routes:
    methods = r.methods if hasattr(r, 'methods') else 'N/A'
    print(f'  - {r.path} [{methods}]')
