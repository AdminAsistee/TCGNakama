import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

async def diagnose():
    admin_token = os.getenv("SHOPIFY_ADMIN_TOKEN")
    store_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
    api_version = "2024-01"
    url = f"{store_url}/admin/api/{api_version}/graphql.json"
    
    headers = {
        "X-Shopify-Access-Token": admin_token,
        "Content-Type": "application/json",
    }
    
    query = "{ shop { name } }"
    
    print(f"Testing Admin API...")
    print(f"URL: {url}")
    print(f"Token (shpat_ part): {admin_token[:10]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"query": query}, headers=headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(f"Response Body: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
