import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
SHOPIFY_STOREFRONT_TOKEN = os.getenv("SHOPIFY_STOREFRONT_TOKEN")
API_VERSION = "2024-01"

async def test_query():
    url = f"{SHOPIFY_STORE_URL}/api/{API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Storefront-Access-Token": SHOPIFY_STOREFRONT_TOKEN,
        "Content-Type": "application/json",
    }
    
    # Simple query to just get store name
    gql_query = """
    {
      shop {
        name
      }
    }
    """
    
    async with httpx.AsyncClient() as client:
        print(f"URL: {url}")
        print(f"Token: {SHOPIFY_STOREFRONT_TOKEN[:8]}...{SHOPIFY_STOREFRONT_TOKEN[-4:]}")
        try:
            response = await client.post(
                url,
                json={"query": gql_query},
                headers=headers
            )
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error Body: {response.text}")
                return

            data = response.json()
            print(f"Data: {data}")
            
            if "errors" in data:
                print(f"Errors: {data['errors']}")
            else:
                print(f"Shop name: {data.get('data', {}).get('shop', {}).get('name')}")

            # Now try products with more detail
            products_query = """
            {
              products(first: 10) {
                edges {
                  node {
                    title
                    handle
                    productType
                    vendor
                    availableForSale
                    tags
                    featuredImage { url }
                    variants(first: 5) {
                      edges {
                        node {
                          id
                          title
                          price { amount }
                          id
                          title
                          price { amount }
                          availableForSale
                          quantityAvailable
                        }
                      }
                    }
                  }
                }
              }
              productTypes(first: 10) {
                edges {
                  node
                }
              }
            }
            """
            response = await client.post(
                url,
                json={"query": products_query},
                headers=headers
            )
            print(f"Products Status: {response.status_code}")
            products_data = response.json()
            if "data" in products_data:
                res = products_data["data"]
                edges = res["products"]["edges"]
                print(f"Found {len(edges)} products")
                for edge in edges:
                    p = edge['node']
                    print(f"--- Product: {p['title']} ---")
                    import json
                    print(json.dumps(p, indent=2))
                
                types = res["productTypes"]["edges"]
                print(f"Product Types: {[t['node'] for t in types]}")

                # Test Cart Creation and Count
                print("\n--- Testing Cart ---")
                cart_mutation = """
                mutation cartCreate($input: CartInput!) {
                  cartCreate(input: $input) {
                    cart {
                      id
                      totalQuantity
                      lines(first: 5) {
                        edges {
                          node {
                            id
                            quantity
                            merchandise {
                              ... on ProductVariant {
                                title
                                product { title }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
                """
                # Use the variant ID from Pichaku if found
                v_id = "gid://shopify/ProductVariant/50469962809591" 
                cart_vars = {"input": {"lines": [{"merchandiseId": v_id, "quantity": 1}]}}
                cart_resp = await client.post(url, json={"query": cart_mutation, "variables": cart_vars}, headers=headers)
                cart_data_json = cart_resp.json()
                print(f"Cart Result: {cart_data_json}")
                
                if "data" in cart_data_json and cart_data_json["data"]["cartCreate"]["cart"]:
                    cart_id = cart_data_json["data"]["cartCreate"]["cart"]["id"]
                    print(f"Created Cart ID: {cart_id}")
                    
                    # Test Clear Cart (Simulate backend logic since we don't have the client method here directly exposed easily without instantiating dependencies)
                    # Actually, we can just run the same mutation we added to dependencies.py to verify it works against Shopify
                    clear_mutation = """
                    mutation cartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {
                      cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
                        cart {
                          id
                          totalQuantity
                          lines(first: 5) {
                            edges {
                              node {
                                id
                              }
                            }
                          }
                        }
                      }
                    }
                    """
                    line_ids = [e["node"]["id"] for e in cart_data_json["data"]["cartCreate"]["cart"]["lines"]["edges"]]
                    if line_ids:
                        print(f"Clearing lines: {line_ids}")
                        clear_vars = {"cartId": cart_id, "lineIds": line_ids}
                        clear_resp = await client.post(url, json={"query": clear_mutation, "variables": clear_vars}, headers=headers)
                        print(f"Clear Cart Result: {clear_resp.json()}")
                    else:
                        print("Cart was already empty, skipping clear test")

            if "errors" in products_data:
                print(f"Product Query Errors: {products_data['errors']}")
            
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_query())
