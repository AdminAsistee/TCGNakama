import os
from dotenv import load_dotenv
load_dotenv()

from app.routers.oauth import get_admin_token

print(f"SHOPIFY_ADMIN_TOKEN in os.environ: {'Yes' if os.getenv('SHOPIFY_ADMIN_TOKEN') else 'No'}")
print(f"get_admin_token() result: {'Yes' if get_admin_token() else 'No'}")
