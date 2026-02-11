import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

async def diagnose():
    # TEST: Try shpss_ token as the access token
    # The user says they have this for their "test antigravity" app which they says "has the scopes"
    shpss_token = os.getenv("SHOPIFY_API_SECRET") 
    store_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
    api_version = "2024-01"
    url = f"{store_url}/admin/api/{api_version}/graphql.json"
    
    headers = {
        "X-Shopify-Access-Token": shpss_token,
        "Content-Type": "application/json",
    }
    
    # Try the restricted fields
    query = """
    {
      shop { name }
      productTypes(first: 5) { edges { node } }
    }
    """
    
    print(f"Testing Admin API with shpss_ token...")
    print(f"URL: {url}")
    print(f"Token Prefix: {shpss_token[:10]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"query": query}, headers=headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
