import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
API_KEY = os.getenv("SHOPIFY_API_KEY")
API_SECRET = os.getenv("SHOPIFY_API_SECRET") # This is often the Private App Password
API_VERSION = "2024-01"

async def get_storefront_token():
    # Admin API endpoint for storefront tokens
    url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/storefront_access_tokens.json"
    
    # Private Apps use Basic Auth: API_KEY:PASSWORD
    # In some cases, API_SECRET provided by user is actually the Password if it starts with shpss_
    
    print(f"Connecting to: {url}")
    print(f"Using API Key: {API_KEY}")
    
    async with httpx.AsyncClient() as client:
        try:
            # Try with Basic Auth
            response = await client.get(
                url,
                auth=(API_KEY, API_SECRET)
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 401:
                # Try setting it as X-Shopify-Access-Token header (for Custom Apps)
                print("Basic Auth failed, trying X-Shopify-Access-Token header...")
                response = await client.get(
                    url,
                    headers={"X-Shopify-Access-Token": API_SECRET}
                )
                print(f"Status (Header): {response.status_code}")

            if response.status_code != 200:
                print(f"Error Body: {response.text}")
                return

            data = response.json()
            tokens = data.get("storefront_access_tokens", [])
            
            if not tokens:
                print("No storefront access tokens found. Attempting to create one...")
                # Create a new one
                create_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/storefront_access_tokens.json"
                create_payload = {
                    "storefront_access_token": {
                        "title": "TCG Nakama Vault Token"
                    }
                }
                
                # Try creating with same auth
                response = await client.post(
                    create_url,
                    auth=(API_KEY, API_SECRET),
                    json=create_payload
                )
                
                if response.status_code == 401:
                    response = await client.post(
                        create_url,
                        headers={"X-Shopify-Access-Token": API_SECRET},
                        json=create_payload
                    )
                
                if response.status_code == 201:
                    token_data = response.json().get("storefront_access_token", {})
                    print(f"SUCCESS! Created new token: {token_data.get('access_token')}")
                else:
                    print(f"Failed to create token: {response.text}")
            else:
                for t in tokens:
                    print(f"FOUND TOKEN: {t.get('title')} -> {t.get('access_token')}")
            
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(get_storefront_token())
