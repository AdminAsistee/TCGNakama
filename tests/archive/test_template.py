"""Test template rendering to find the error"""
from jinja2 import Template, Environment, FileSystemLoader
import os

# Set up Jinja environment
template_dir = r"c:\Users\amrca\Documents\antigravity\tcgnakama\app\templates\admin"
env = Environment(loader=FileSystemLoader(template_dir))

try:
    # Try to load the template
    template = env.get_template("bulk_upload.html")
    print("[OK] Template loaded successfully")
    
    # Try to render with minimal context
    class FakeRequest:
        pass
    
    context = {
        "request": FakeRequest(),
        "collections": ["Pokemon", "One Piece", "Magic"]
    }
    
    rendered = template.render(context)
    print("[OK] Template rendered successfully")
    print(f"[OK] Rendered length: {len(rendered)} characters")
    
except Exception as e:
    print(f"[ERROR] {type(e).__name__}")
    print(f"[ERROR] Message: {str(e)}")
    import traceback
    traceback.print_exc()
