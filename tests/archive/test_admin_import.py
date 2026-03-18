"""Check if admin.py has any import or syntax errors"""
import sys
sys.path.insert(0, r'c:\Users\amrca\Documents\antigravity\tcgnakama')

try:
    print("Importing admin module...")
    from app.routers import admin
    print("[OK] Admin module imported successfully")
    
    print("\nChecking bulk_upload_page function...")
    import inspect
    sig = inspect.signature(admin.bulk_upload_page)
    print(f"[OK] Function signature: {sig}")
    print(f"[OK] Parameters: {list(sig.parameters.keys())}")
    
except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
