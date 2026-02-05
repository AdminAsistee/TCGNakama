import os
import httpx
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
SHOPIFY_STOREFRONT_TOKEN = os.getenv("SHOPIFY_STOREFRONT_TOKEN")
API_VERSION = "2024-01"

class ShopifyClient:
    _client = None

    def __init__(self):
        self.url = f"{SHOPIFY_STORE_URL}/api/{API_VERSION}/graphql.json"
        self.headers = {
            "X-Shopify-Storefront-Access-Token": SHOPIFY_STOREFRONT_TOKEN,
            "Content-Type": "application/json",
        }

    @classmethod
    def get_client(cls):
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_connections=10, max_keepalive_connections=5))
        return cls._client

    async def _query(self, query: str, variables: Optional[dict] = None) -> dict:
        if not SHOPIFY_STOREFRONT_TOKEN:
             raise Exception("Missing Shopify Storefront Token")
        
        client = self.get_client()
        try:
            response = await client.post(
                self.url,
                json={"query": query, "variables": variables},
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                print(f"Shopify API returned errors: {data['errors']}")
                # If we have data, we can proceed (partial success)
                if "data" not in data or not data["data"]:
                     raise Exception(f"Shopify API Error: {data['errors']}")
            return data["data"]
        except httpx.TimeoutException:
            print("Shopify API request timed out")
            raise Exception("Shopify API request timed out")
        except Exception as e:
            print(f"Shopify API Request Error: {e}")
            raise

    def _map_product(self, node: dict) -> dict:
        # Extract fields from Shopify response
        variants = node.get("variants", {}).get("edges", [])
        variant = variants[0]["node"] if variants else {}
        
        # Shopify tags often contain TCG metadata in this format: set:Base Set, rarity:Epic
        tags = node.get("tags", [])
        card_set = "Unknown Set"
        rarity = "Common"
        card_number = "#000"
        
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower.startswith("set:"):
                card_set = tag.split(":")[1].strip()
            elif tag_lower.startswith("rarity:"):
                rarity = tag.split(":")[1].strip()
            elif tag_lower.startswith("number:"):
                card_number = tag.split(":")[1].strip()

        return {
            "id": node["id"],
            "safe_id": node["id"].split("/")[-1],
            "variant_id": variant.get("id"),
            "title": node["title"],
            "set": card_set,
            "rarity": rarity,
            "price": float(variant.get("price", {}).get("amount", 0)),
            "image": node.get("featuredImage", {}).get("url") if node.get("featuredImage") else "https://images.pokemontcg.io/bg.jpg",
            "badge": rarity.upper(),
            "badge_color": "bg-primary" if rarity == "Common" else "bg-green-500",
            "card_number": card_number,
            "card_number": card_number,
            "status": "Sync" if variant.get("availableForSale") else "Sold Out",
            "images": [img["node"]["url"] for img in node.get("images", {}).get("edges", [])] if node.get("images", {}).get("edges") else ([node.get("featuredImage", {}).get("url")] if node.get("featuredImage") else ["https://images.pokemontcg.io/bg.jpg"])
        }

    async def get_products(self, query: Optional[str] = None, rarity: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[dict]:
        # Broaden search: remove type restriction for initial debugging
        search_query = ""
        if query:
            search_query += f" (title:*{query}*)"
        if rarity:
            # Use quotes for tags with spaces
            if search_query: search_query += " AND "
            search_query += f'(tag:"rarity:{rarity}")'
        
        # Default to empty string for GraphQL if no filters
        if not search_query:
            search_query = "" 
        
        gql_query = """
        query getProducts($query: String!) {
          products(first: 50, query: $query) {
            edges {
              node {
                id
                title
                tags
                handle
                featuredImage {
                  url
                }
                images(first: 10) {
                  edges {
                    node {
                      url
                    }
                  }
                }
                variants(first: 1) {
                  edges {
                    node {
                      id
                      availableForSale
                      price {
                        amount
                        currencyCode
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        try:
            print(f"Querying Shopify with: {search_query}")
            data = await self._query(gql_query, {"query": search_query})
            products = [self._map_product(edge["node"]) for edge in data["products"]["edges"]]
            
            # Fallback/Development: Include mock products if Shopify is empty or for local testing visibility
            if not products and not query and not rarity:
                from app.utils.mock_data import MOCK_PRODUCTS
                products = MOCK_PRODUCTS + products
                print(f"Shopify empty, injected {len(MOCK_PRODUCTS)} mock products for visibility")
            
            print(f"Successfully fetched {len(products)} products")
        except Exception as e:
            print(f"Error fetching products from Shopify: {e}")
            raise
            
        # Post-fetch refining (ensures perfect consistency across Shopify & Mock)
        if query:
            q = query.lower()
            products = [p for p in products if q in p['title'].lower() or q in p['set'].lower()]
        if rarity:
            products = [p for p in products if rarity.lower() == p['rarity'].lower()]
        if min_price is not None:
            products = [p for p in products if p['price'] >= min_price]
        if max_price is not None:
            products = [p for p in products if p['price'] <= max_price]
            
        return products

    async def get_product(self, product_id: str) -> Optional[dict]:
        if product_id.startswith("mock_"):
            from app.utils.mock_data import MOCK_PRODUCTS
            return next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)

        gql_query = """
        query getProduct($id: ID!) {
          product(id: $id) {
            id
            title
            tags
            handle
            handle
            featuredImage { url }
            images(first: 10) {
              edges {
                node {
                  url
                }
              }
            }
            variants(first: 1) {
              edges {
                node {
                  id
                  price { amount currencyCode }
                }
              }
            }
          }
        }
        """
        try:
            data = await self._query(gql_query, {"id": product_id})
            return self._map_product(data["product"])
        except Exception as e:
            print(f"Error fetching product: {e}")
            return None

    async def create_cart(self, variant_id: str, quantity: int = 1) -> dict:
        if variant_id.startswith("gid://shopify/ProductVariant/"):
            # Mock check
            mock_ids = ["123456789", "223456789", "323456789", "423456789", "523456789", "623456789"]
            if any(vid in variant_id for vid in mock_ids):
                return {"id": "mock-cart", "checkoutUrl": f"{SHOPIFY_STORE_URL}/cart", "totalQuantity": quantity}

        gql_query = """
        mutation cartCreate($input: CartInput!) {
          cartCreate(input: $input) {
            cart {
              id
              checkoutUrl
              totalQuantity
              lines(first: 20) {
                edges {
                  node {
                    id
                    quantity
                    merchandise {
                      ... on ProductVariant {
                        id
                        title
                        price { amount }
                        product {
                          title
                          tags
                          featuredImage { url }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
       """
        variables = {"input": {"lines": [{"merchandiseId": variant_id, "quantity": quantity}]}}
        try:
            data = await self._query(gql_query, variables)
            return data["cartCreate"]["cart"]
        except Exception as e:
            print(f"Error creating cart: {e}")
            return {"id": "fallback-cart", "checkoutUrl": f"{SHOPIFY_STORE_URL}/cart", "totalQuantity": 0}

    async def add_to_existing_cart(self, cart_id: str, variant_id: str, quantity: int = 1) -> dict:
        if cart_id == "mock-cart" or cart_id == "fallback-cart":
             return {"id": cart_id, "checkoutUrl": f"{SHOPIFY_STORE_URL}/cart", "totalQuantity": 2}

        gql_query = """
        mutation cartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
          cartLinesAdd(cartId: $cartId, lines: $lines) {
            cart {
              id
              checkoutUrl
              totalQuantity
              lines(first: 20) {
                edges {
                  node {
                    id
                    quantity
                    merchandise {
                      ... on ProductVariant {
                        id
                        title
                        price { amount }
                        product {
                          title
                          tags
                          featuredImage { url }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
       """
        variables = {
            "cartId": cart_id,
            "lines": [{"merchandiseId": variant_id, "quantity": quantity}]
        }
        try:
            data = await self._query(gql_query, variables)
            return data["cartLinesAdd"]["cart"]
        except Exception as e:
            print(f"Error adding to cart: {e}")
            return {"id": cart_id, "checkoutUrl": f"{SHOPIFY_STORE_URL}/cart", "totalQuantity": 1}

    async def update_cart_line(self, cart_id: str, line_id: str, quantity: int) -> dict:
        if cart_id == "mock-cart" or cart_id == "fallback-cart":
             return {"id": cart_id, "checkoutUrl": f"{SHOPIFY_STORE_URL}/cart", "totalQuantity": quantity}

        gql_query = """
        mutation cartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
          cartLinesUpdate(cartId: $cartId, lines: $lines) {
            cart {
              id
              checkoutUrl
              totalQuantity
              lines(first: 20) {
                edges {
                  node {
                    id
                    quantity
                    merchandise {
                      ... on ProductVariant {
                        id
                        title
                        price { amount }
                        product {
                          title
                          tags
                          featuredImage { url }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {
            "cartId": cart_id,
            "lines": [{"id": line_id, "quantity": quantity}]
        }
        try:
            data = await self._query(gql_query, variables)
            return data["cartLinesUpdate"]["cart"]
        except Exception as e:
            print(f"Error updating cart line: {e}")
            return None

    async def clear_cart(self, cart_id: str) -> dict:
        if cart_id == "mock-cart":
             return {"id": "mock-cart", "checkoutUrl": f"{SHOPIFY_STORE_URL}/cart", "totalQuantity": 0, "lines": {"edges": []}}

        # First, fetch the cart to get all line IDs
        cart = await self.get_cart(cart_id)
        if not cart:
            return None
            
        line_ids = [edge["node"]["id"] for edge in cart.get("lines", {}).get("edges", [])]
        
        if not line_ids:
            return cart # Already empty

        gql_query = """
        mutation cartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {
          cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
            cart {
              id
              checkoutUrl
              totalQuantity
              lines(first: 20) {
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
        variables = {
            "cartId": cart_id,
            "lineIds": line_ids
        }
        try:
            data = await self._query(gql_query, variables)
            return data["cartLinesRemove"]["cart"]
        except Exception as e:
            print(f"Error clearing cart: {e}")
            return None

    async def get_cart(self, cart_id: str) -> Optional[dict]:
        if cart_id == "mock-cart":
            # For mock testing, return a dummy but populated cart
            return {
                "id": "mock-cart",
                "checkoutUrl": f"{SHOPIFY_STORE_URL}/cart",
                "totalQuantity": 2,
                "lines": {
                    "edges": [
                        {
                            "node": {
                                "quantity": 1,
                                "merchandise": {
                                    "id": "gid://shopify/ProductVariant/123456789",
                                    "title": "Charizard 1st Ed.",
                                    "price": {"amount": "3750000.0"},
                                    "product": {
                                        "title": "Charizard 1st Ed.",
                                        "tags": ["set:Base Set", "rarity:Ultra Rare"],
                                        "featuredImage": {"url": "https://lh3.googleusercontent.com/aida-public/AB6AXuBnlxbCCW7ccJLac_9xcLOXxM-MQgVnouqpyKkiCDfy4FfqfF-di-JUgJIqWJ8lCnc_HYiWlsxm5jCjWF56iaORuRVkL_kbOB-RBc9rxKCLj0jPzxQ1ClNuMffzy_F0XUAW8RgtTJUIN8Ec2cIxTKENalMJzzdGbAl9Eq87pK2r5s6Gmo9cNEupS31EY89f5KlNZv6Q2sSYz5mfZH3RN51Tj1fLS6U82OqUoiU5toqg6brAXMD5VihYlGsJCQzBKrRuPvi1aTztNq19"}
                                    }
                                }
                            }
                        }
                    ]
                }
            }

        gql_query = """
        query getCart($cartId: ID!) {
          cart(id: $cartId) {
            id
            checkoutUrl
            totalQuantity
            lines(first: 20) {
              edges {
                node {
                  id
                  quantity
                  merchandise {
                    ... on ProductVariant {
                      id
                      title
                      price { amount }
                      product {
                        id
                        title
                        tags
                        featuredImage { url }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        try:
            data = await self._query(gql_query, {"cartId": cart_id})
            return data.get("cart")
        except Exception as e:
            print(f"Error fetching cart: {e}")
            return None

def get_shopify_client() -> ShopifyClient:
    return ShopifyClient()
