#!/usr/bin/env python3
"""Insert bulk upload routes into admin.py"""

# Read the bulk upload routes
with open('bulk_upload_routes.py', 'r', encoding='utf-8') as f:
    bulk_routes = f.read()

# Read admin.py
with open('app/routers/admin.py', 'r', encoding='utf-8') as f:
    admin_content = f.read()

# Find the insertion point (after save_grade function)
insertion_marker = '        return JSONResponse({"success": False, "error": str(e)}, status_code=500)\n\n\n@router.post("/appraise-market/{product_id}")'

if insertion_marker in admin_content:
    # Insert the bulk upload routes
    admin_content = admin_content.replace(
        insertion_marker,
        f'        return JSONResponse({{"success": False, "error": str(e)}}), status_code=500)\n\n\n# ============================================================================\n# BULK UPLOAD ROUTES\n# ============================================================================\n\n{bulk_routes}\n\n@router.post("/appraise-market/{{product_id}}")'
    )
    print("SUCCESS: Inserted bulk upload routes")
else:
    print("ERROR: Could not find insertion point")
    print("Searching for similar patterns...")
    if "@router.post(\"/appraise-market" in admin_content:
        print("  - Found appraise-market route")

# Write back
with open('app/routers/admin.py', 'w', encoding='utf-8') as f:
    f.write(admin_content)

print("\nDone! Routes added to admin.py")
