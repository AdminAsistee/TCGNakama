import os
import httpx
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
SHOPIFY_STOREFRONT_TOKEN = os.getenv("SHOPIFY_STOREFRONT_TOKEN")
API_VERSION = "2024-01"

def safe_print(message: str):
    """Print with Unicode error handling for Windows cp932 codec."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII with backslashreplace for Unicode chars
        print(message.encode('ascii', 'backslashreplace').decode('ascii'))


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
                print(f"Shopify API returned errors: {str(data['errors']).encode('ascii', 'backslashreplace').decode()}")
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
        condition = None
        
        for tag in tags:
            tag_lower = tag.lower()
            if ":" in tag:
                key, value = tag.split(":", 1)
                key = key.strip().lower()
                val = value.strip()
                
                if key == "set":
                    card_set = val
                elif key == "rarity":
                    rarity = val
                elif key == "number":
                    card_number = val
                elif key == "condition":
                    condition = val

        # DEBUG: Log the first variant to see what Shopify is sending
        if variants:
            v0 = variants[0]["node"]
            # Removed print statement that caused UnicodeEncodeError on Windows

        # Calculate total inventory from all variants
        total_inventory = 0
        for edge in variants:
            v_node = edge.get("node", {})
            qty = v_node.get("quantityAvailable")
            # If any variant is tracked (not None), we add it. 
            # If it's None, it usually means "untracked" (unlimited).
            # For this dashboard, let's treat None as 0 for summing, 
            # or we could flag it. Let's stick to 0 for now as per previous fix.
            if qty is not None:
                total_inventory += qty

        return {
            "id": node["id"],
            "safe_id": node["id"].split("/")[-1],
            "variant_id": variant.get("id"),
            "title": node["title"],
            "set": card_set,
            "rarity": rarity,
            "condition": condition,
            "price": float(variant.get("price", {}).get("amount", 0)),
            "image": node.get("featuredImage", {}).get("url") if node.get("featuredImage") else "https://images.pokemontcg.io/bg.jpg",
            "badge": rarity.upper(),
            "badge_color": "bg-primary" if rarity == "Common" else "bg-green-500",
            "card_number": card_number,
            "totalInventory": total_inventory,
            "createdAt": node.get("createdAt"),
            "status": "Sync" if variant.get("availableForSale") else "Sold Out",
            "tags": node.get("tags", []),
            "images": [img["node"]["url"] for img in node.get("images", {}).get("edges", [])] if node.get("images", {}).get("edges") else ([node.get("featuredImage", {}).get("url")] if node.get("featuredImage") else ["https://images.pokemontcg.io/bg.jpg"]),
            "vendor": node.get("vendor", "TCG Nakama"),
            "collections": [coll["node"]["title"] for coll in node.get("collections", {}).get("edges", [])] if node.get("collections", {}).get("edges") else []
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
                createdAt
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
                variants(first: 10) {
                  edges {
                    node {
                      id
                      availableForSale
                      quantityAvailable
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
            # if not products and not query and not rarity:
            #     from app.utils.mock_data import MOCK_PRODUCTS
            #     products = MOCK_PRODUCTS + products
            #     print(f"Shopify empty, injected {len(MOCK_PRODUCTS)} mock products for visibility")
            
            print(f"Successfully fetched {len(products)} products")
        except Exception as e:
            print(f"Error fetching products from Shopify: {e}. Falling back to mock data.")
            from app.utils.mock_data import MOCK_PRODUCTS
            products = MOCK_PRODUCTS
            
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

    async def get_collections(self, first: int = 50) -> List[dict]:
        gql_query = """
        query getCollections($first: int!) {
          collections(first: $first) {
            edges {
              node {
                id
                handle
                title
                description
                image {
                  url
                }
              }
            }
          }
        }
        """
        try:
            # Note: int! in GraphQL schema might need to be Int!
            gql_query = gql_query.replace("$first: int!", "$first: Int!")
            data = await self._query(gql_query, {"first": first})
            collections = []
            for edge in data["collections"]["edges"]:
                node = edge["node"]
                collections.append({
                    "id": node["id"],
                    "handle": node["handle"],
                    "title": node["title"],
                    "description": node.get("description", ""),
                    "image": node.get("image", {}).get("url") if node.get("image") else None
                })
            print(f"Successfully fetched {len(collections)} collections")
            return collections
        except Exception as e:
            print(f"Error fetching collections from Shopify: {e}")
            raise

    async def get_collection_products(self, handle: str, first: int = 50) -> List[dict]:
        gql_query = """
        query getCollectionProducts($handle: String!, $first: Int!) {
          collection(handle: $handle) {
            products(first: $first) {
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
        }
        """
        try:
            data = await self._query(gql_query, {"handle": handle, "first": first})
            if not data or not data.get("collection"):
                print(f"Collection with handle '{handle}' not found.")
                return []
            
            products = [self._map_product(edge["node"]) for edge in data["collection"]["products"]["edges"]]
            print(f"Successfully fetched {len(products)} products from collection '{handle}'")
            return products
        except Exception as e:
            print(f"Error fetching products from collection '{handle}': {e}")
            raise

    async def get_product(self, product_id: str) -> Optional[dict]:
        if product_id.startswith("mock_"):
            from app.utils.mock_data import MOCK_PRODUCTS
            return next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)

        gql_query = """
        query getProduct($id: ID!) {
          product(id: $id) {
            id
            title
            descriptionHtml
            tags
            handle
            vendor
            totalInventory
            featuredImage { url }
            images(first: 10) {
              edges {
                node {
                  url
                }
              }
            }
            collections(first: 10) {
              edges {
                node {
                  title
                }
              }
            }
            variants(first: 10) {
              edges {
                node {
                  id
                  price { amount currencyCode }
                  availableForSale
                }
              }
            }
          }
        }
        """
        try:
            print(f"[DEBUG] Fetching product with ID: {product_id}")
            data = await self._query(gql_query, {"id": product_id})
            
            # Check if product exists in response
            if not data or not data.get("product"):
                print(f"[ERROR] Product not found in Shopify response for ID: {product_id}")
                print(f"[DEBUG] Response data: {data}")
                return None
            
            
            # Debug: Check what collections data looks like
            print(f"[DEBUG] Raw collections from GraphQL: {data['product'].get('collections', {})}")
            
            product = self._map_product(data["product"])
            # Add description for editing - convert HTML to plain text with newlines
            description_html = data["product"].get("descriptionHtml", "")
            # Convert <br> tags to newlines for textarea display
            description_plain = description_html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
            # Remove any other HTML tags (simple approach)
            import re
            description_plain = re.sub(r'<[^>]+>', '', description_plain)
            product["description"] = description_plain
            # Add inventory quantity from product totalInventory
            product["inventory_quantity"] = data["product"].get("totalInventory", 0)
            
            print(f"[DEBUG] Successfully fetched product: {product.get('title')}")
            return product
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

    async def get_collections(self, admin_token: Optional[str] = None) -> List[dict | str]:
        """
        Fetch collections from Shopify.
        If admin_token is provided, uses Admin API and returns titles as strings.
        If not, uses Storefront API and returns full objects.
        """
        if admin_token:
            # Admin API Logic (returns strings for the 'Add Card' dropdown)
            admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
            headers = {
                "X-Shopify-Access-Token": admin_token,
                "Content-Type": "application/json",
            }

            query = """
            {
              collections(first: 250) {
                edges {
                  node {
                    title
                  }
                }
              }
            }
            """

            client = self.get_client()
            try:
                response = await client.post(
                    admin_url,
                    json={"query": query},
                    headers=headers
                )
                response.raise_for_status()
                res_data = response.json()
                
                if "errors" in res_data:
                    raise Exception(f"Shopify Admin API Error: {res_data['errors']}")
                
                collections = res_data["data"]["collections"]["edges"]
                return [c["node"]["title"] for c in collections if c["node"]]
            except Exception as e:
                print(f"Error fetching collections (Admin): {str(e).encode('ascii', 'backslashreplace').decode()}")
                return ["Pokémon", "One Piece", "Magic: TG", "Yu-Gi-Oh!"] # Fallback

        else:
            # Storefront API Logic (returns objects with titles, handles, and images)
            query = """
            {
              collections(first: 250) {
                edges {
                  node {
                    title
                    handle
                    image {
                      url
                    }
                  }
                }
              }
            }
            """
            try:
                data = await self._query(query)
                collections = []
                for edge in data.get("collections", {}).get("edges", []):
                    node = edge.get("node", {})
                    collections.append({
                        "title": node.get("title"),
                        "handle": node.get("handle"),
                        "image": node.get("image", {}).get("url") if node.get("image") else None
                    })
                return collections
            except Exception as e:
                print(f"Error fetching collections (Storefront): {e}")
                return []

    async def get_product_types(self, admin_token: str) -> List[str]:
        """
        Fetch unique product types from Shopify using the Admin API.
        """
        admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": admin_token,
            "Content-Type": "application/json",
        }

        query = """
        {
          productTypes(first: 250) {
            edges {
              node
            }
          }
        }
        """

        client = self.get_client()
        try:
            response = await client.post(
                admin_url,
                json={"query": query},
                headers=headers
            )
            response.raise_for_status()
            res_data = response.json()
            
            if "errors" in res_data:
                raise Exception(f"Shopify Admin API Error: {res_data['errors']}")
            
            types = res_data["data"]["productTypes"]["edges"]
            return [t["node"] for t in types if t["node"]]
        except Exception as e:
            print(f"Error fetching product types: {str(e).encode('ascii', 'backslashreplace').decode()}")
            return ["Pokémon", "One Piece", "Magic: TG", "Yu-Gi-Oh!"] # Fallback

    async def staged_uploads_create(self, admin_token: str, filename: str, mime_type: str, file_size: str) -> dict:
        """
        Prepare a staged upload for product media.
        """
        admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": admin_token,
            "Content-Type": "application/json",
        }

        mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets {
              url
              resourceUrl
              parameters {
                name
                value
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        variables = {
            "input": [
                {
                    "filename": filename,
                    "mimeType": mime_type,
                    "resource": "PRODUCT_IMAGE",
                    "fileSize": file_size,
                    "httpMethod": "POST"
                }
            ]
        }

        client = self.get_client()
        try:
            response = await client.post(
                admin_url,
                json={"query": mutation, "variables": variables},
                headers=headers
            )
            response.raise_for_status()
            res_data = response.json()
            
            if "errors" in res_data:
                raise Exception(f"Shopify Admin API Error: {res_data['errors']}")
            
            result = res_data["data"]["stagedUploadsCreate"]
            if result.get("userErrors"):
                raise Exception(f"Shopify User Error: {result['userErrors']}")

            return result["stagedTargets"][0]
        except Exception as e:
            print(f"Error creating staged upload: {e}")
            raise

    async def upload_file_to_staged_target(self, target: dict, file_content: bytes, mime_type: str) -> str:
        """
        Upload the actual file content to the staged target URL provided by Shopify.
        Returns the resourceUrl to be used in product creation.
        """
        url = target["url"]
        parameters = target["parameters"]
        
        # Prepare multipart/form-data
        data = {}
        for param in parameters:
            data[param["name"]] = param["value"]
        
        # The 'file' MUST be the last parameter for some storage providers (like Google Cloud Storage)
        files = {"file": ("filename", file_content, mime_type)}
        
        client = httpx.AsyncClient(timeout=60.0) # Using a new client or the shared one
        try:
            # Note: Staged uploads use a regular POST, not the Shopify GraphQL headers
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
            return target["resourceUrl"]
        except Exception as e:
            print(f"Error uploading file to staged target: {e}")
            raise
        finally:
            await client.aclose()

    async def create_product(self, admin_token: str, product_data: dict) -> dict:
        """
        Create a new product in Shopify using the Admin API.
        product_data should contain: title, description, price, vendor, product_type, tags, sku, quantity, images (list of URLs or resource URLs)
        """
        admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": admin_token,
            "Content-Type": "application/json",
        }

        # Build GraphQL mutation
        mutation = """
        mutation productCreate($input: ProductInput!, $media: [CreateMediaInput!]) {
          productCreate(input: $input, media: $media) {
            product {
              id
              title
              variants(first: 1) {
                edges {
                  node {
                    id
                    inventoryItem {
                      id
                    }
                  }
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        # Prepare variables (ProductInput in 2024-01 does NOT have variants)
        variables = {
            "input": {
                "title": product_data["title"],
                "descriptionHtml": product_data.get("description", ""),
                "vendor": product_data.get("vendor", "TCG Nakama"),
                "productType": product_data.get("product_type", "Collectible Card"),
                "tags": product_data.get("tags", [])
            }
        }

        # Add media
        media = []
        for img_source in product_data.get("images", []):
            if img_source:
                media.append({
                    "mediaContentType": "IMAGE",
                    "originalSource": img_source
                })

        # Fallback to single image if 'images' not provided but 'image_url' is
        if not media and product_data.get("image_url"):
            media.append({
                "mediaContentType": "IMAGE",
                "originalSource": product_data["image_url"]
            })

        client = self.get_client()
        try:
            # 1. Create the product
            response = await client.post(
                admin_url,
                json={"query": mutation, "variables": {"input": variables["input"], "media": media if media else None}},
                headers=headers
            )
            response.raise_for_status()
            res_data = response.json()
            
            if "errors" in res_data:
                raise Exception(f"Shopify Admin API Error: {res_data['errors']}")
            
            result = res_data["data"]["productCreate"]
            if result.get("userErrors"):
                raise Exception(f"Shopify User Error: {result['userErrors']}")

            product = result["product"]
            variant_id = product["variants"]["edges"][0]["node"]["id"]
            inventory_item_id = product["variants"]["edges"][0]["node"]["inventoryItem"]["id"]

            # 2. Update the default variant price
            variant_mutation = """
            mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
              productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                productVariants {
                  id
                  price
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            # Ensure price is valid
            price_value = product_data.get("price")
            if price_value is None or price_value == "":
                price_value = 0
            
            variant_vars = {
                "productId": product["id"],
                "variants": [
                    {
                        "id": variant_id,
                        "price": str(price_value)
                    }
                ]
            }
            
            var_resp = await client.post(
                admin_url,
                json={"query": variant_mutation, "variables": variant_vars},
                headers=headers
            )
            var_data = var_resp.json()
            if "errors" in var_data:
                print(f"Warning: Failed to update variant price: {var_data['errors']}")
            elif var_data.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors"):
                print(f"Warning: Shopify User Error updating variant: {var_data['data']['productVariantsBulkUpdate']['userErrors']}")

            # 2.5. Enable inventory tracking on the inventory item
            inventory_item_mutation = """
            mutation inventoryItemUpdate($id: ID!, $input: InventoryItemInput!) {
              inventoryItemUpdate(id: $id, input: $input) {
                inventoryItem {
                  id
                  tracked
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            inventory_item_vars = {
                "id": inventory_item_id,
                "input": {
                    "tracked": True
                }
            }
            
            inv_item_resp = await client.post(
                admin_url,
                json={"query": inventory_item_mutation, "variables": inventory_item_vars},
                headers=headers
            )
            inv_item_data = inv_item_resp.json()
            if "errors" in inv_item_data:
                print(f"Warning: Failed to enable inventory tracking: {inv_item_data['errors']}")
            elif inv_item_data.get("data", {}).get("inventoryItemUpdate", {}).get("userErrors"):
                print(f"Warning: Shopify User Error enabling tracking: {inv_item_data['data']['inventoryItemUpdate']['userErrors']}")
            else:
                print(f"[DEBUG] Inventory tracking enabled on inventory item")

            # 3. Update inventory if quantity > 0
            quantity = product_data.get("quantity", 1)
            if quantity > 0:
                await self._update_inventory(admin_token, inventory_item_id, quantity)

            # 4. Assign product to selected collections
            collections = product_data.get("collections", [])
            if collections:
                await self._assign_to_collections(admin_token, product["id"], collections)

            # 5. Publish to all sales channels
            await self._publish_to_all_channels(admin_token, product["id"])

            return product
        except Exception as e:
            print(f"Error creating product: {str(e).encode('ascii', 'backslashreplace').decode()}")
            raise

    async def _publish_to_all_channels(self, admin_token: str, product_id: str):
        """Publish a product to all available sales channels."""
        admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": admin_token,
            "Content-Type": "application/json",
        }
        
        try:
            # First, get all publication IDs (sales channels)
            publications_query = """
            query {
              publications(first: 10) {
                edges {
                  node {
                    id
                    name
                  }
                }
              }
            }
            """
            
            client = self.get_client()
            pub_res = await client.post(admin_url, json={"query": publications_query}, headers=headers)
            pub_res.raise_for_status()
            pub_data = pub_res.json()
            
            if "errors" in pub_data:
                print(f"Error fetching publications: {pub_data['errors']}")
                return
            
            publication_ids = []
            for edge in pub_data.get("data", {}).get("publications", {}).get("edges", []):
                node = edge["node"]
                publication_ids.append(node["id"])
                print(f"[DEBUG] Found sales channel: {node['name']}")
            
            if not publication_ids:
                print("[WARNING] No sales channels found")
                return
            
            # Publish to all channels
            publish_mutation = """
            mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
              publishablePublish(id: $id, input: $input) {
                publishable {
                  availablePublicationsCount {
                    count
                  }
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            
            publish_input = [{"publicationId": pub_id} for pub_id in publication_ids]
            publish_vars = {
                "id": product_id,
                "input": publish_input
            }
            
            publish_res = await client.post(
                admin_url,
                json={"query": publish_mutation, "variables": publish_vars},
                headers=headers
            )
            publish_res.raise_for_status()
            publish_data = publish_res.json()
            
            if "errors" in publish_data:
                print(f"Error publishing to sales channels: {publish_data['errors']}")
            else:
                result = publish_data.get("data", {}).get("publishablePublish", {})
                if result.get("userErrors"):
                    print(f"User errors publishing: {result['userErrors']}")
                else:
                    count = result.get("publishable", {}).get("availablePublicationsCount", {}).get("count", 0)
                    print(f"[SUCCESS] Product published to {len(publication_ids)} sales channels")
                    
        except Exception as e:
            print(f"Exception publishing to sales channels: {str(e).encode('ascii', 'backslashreplace').decode()}")

    async def _assign_to_collections(self, admin_token: str, product_id: str, collection_titles: List[str]):
        """Assign a product to multiple collections by their titles."""
        admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": admin_token,
            "Content-Type": "application/json",
        }
        
        try:
            # First, fetch all collections to get their IDs
            collections_query = """
            query {
              collections(first: 250) {
                edges {
                  node {
                    id
                    title
                  }
                }
              }
            }
            """
            
            client = self.get_client()
            coll_res = await client.post(admin_url, json={"query": collections_query}, headers=headers)
            coll_res.raise_for_status()
            coll_data = coll_res.json()
            
            if "errors" in coll_data:
                print(f"Error fetching collections for assignment: {coll_data['errors']}")
                return
            
            # Build a map of title -> ID
            collection_map = {}
            for edge in coll_data.get("data", {}).get("collections", {}).get("edges", []):
                node = edge["node"]
                collection_map[node["title"]] = node["id"]
            
            # Get collection IDs for the selected titles
            collection_ids = [collection_map[title] for title in collection_titles if title in collection_map]
            
            if not collection_ids:
                print(f"[WARNING] No matching collections found for: {collection_titles}")
                return
            
            # Assign product to collections
            for collection_id in collection_ids:
                assign_mutation = """
                mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
                  collectionAddProducts(id: $id, productIds: $productIds) {
                    collection {
                      id
                      title
                    }
                    userErrors {
                      field
                      message
                    }
                  }
                }
                """
                assign_vars = {
                    "id": collection_id,
                    "productIds": [product_id]
                }
                
                assign_res = await client.post(
                    admin_url,
                    json={"query": assign_mutation, "variables": assign_vars},
                    headers=headers
                )
                assign_res.raise_for_status()
                assign_data = assign_res.json()
                
                if "errors" in assign_data:
                    print(f"Error assigning to collection: {assign_data['errors']}")
                else:
                    result = assign_data.get("data", {}).get("collectionAddProducts", {})
                    if result.get("userErrors"):
                        print(f"User errors assigning to collection: {result['userErrors']}")
                    else:
                        coll_title = result.get("collection", {}).get("title", "Unknown")
                        print(f"[SUCCESS] Product assigned to collection: {coll_title}")
                        
        except Exception as e:
            print(f"Exception assigning to collections: {str(e).encode('ascii', 'backslashreplace').decode()}")

    async def _update_inventory(self, admin_token: str, inventory_item_id: str, quantity: int):
        """Update inventory levels for a product variant."""
        admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": admin_token,
            "Content-Type": "application/json",
        }

        # First we need the location ID
        location_query = "{ locations(first: 1) { edges { node { id } } } }"
        client = self.get_client()
        
        try:
            loc_res = await client.post(admin_url, json={"query": location_query}, headers=headers)
            loc_res.raise_for_status()
            loc_data = loc_res.json()
            
            if "errors" in loc_data:
                print(f"Error fetching locations: {loc_data['errors']}")
                return
                
            if not loc_data.get("data", {}).get("locations", {}).get("edges"):
                print("No locations found, skipping inventory update")
                return

            location_id = loc_data["data"]["locations"]["edges"][0]["node"]["id"]
            print(f"[DEBUG] Setting inventory: item={inventory_item_id}, location={location_id}, quantity={quantity}")

            # Step 1: Activate inventory tracking for this item at this location
            activate_mutation = """
            mutation inventoryActivate($inventoryItemId: ID!, $locationId: ID!) {
              inventoryActivate(inventoryItemId: $inventoryItemId, locationId: $locationId) {
                inventoryLevel {
                  id
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            activate_vars = {
                "inventoryItemId": inventory_item_id,
                "locationId": location_id
            }
            
            activate_res = await client.post(
                admin_url,
                json={"query": activate_mutation, "variables": activate_vars},
                headers=headers
            )
            activate_res.raise_for_status()
            activate_data = activate_res.json()
            
            if "errors" in activate_data:
                print(f"Error activating inventory tracking: {activate_data['errors']}")
                # Continue anyway - it might already be activated
            else:
                activate_result = activate_data.get("data", {}).get("inventoryActivate", {})
                if activate_result.get("userErrors"):
                    print(f"User errors activating inventory: {activate_result['userErrors']}")
                else:
                    print(f"[DEBUG] Inventory tracking activated")

            # Step 2: Set the inventory level
            inventory_mutation = """
            mutation inventorySetOnHandQuantities($input: InventorySetOnHandQuantitiesInput!) {
              inventorySetOnHandQuantities(input: $input) {
                userErrors {
                  field
                  message
                }
              }
            }
            """
            inventory_vars = {
                "input": {
                    "reason": "correction",
                    "setQuantities": [
                        {
                            "inventoryItemId": inventory_item_id,
                            "locationId": location_id,
                            "quantity": quantity
                        }
                    ]
                }
            }

            inv_res = await client.post(
                admin_url,
                json={"query": inventory_mutation, "variables": inventory_vars},
                headers=headers
            )
            inv_res.raise_for_status()
            inv_data = inv_res.json()
            
            if "errors" in inv_data:
                print(f"Error updating inventory: {inv_data['errors']}")
                return
                
            result = inv_data.get("data", {}).get("inventorySetOnHandQuantities", {})
            if result.get("userErrors"):
                print(f"User errors updating inventory: {result['userErrors']}")
            else:
                print(f"[SUCCESS] Inventory updated to {quantity}")
                
        except Exception as e:
            print(f"Exception updating inventory: {str(e).encode('ascii', 'backslashreplace').decode()}")

    async def _increment_inventory(self, admin_token: str, inventory_item_id: str, quantity_to_add: int):
        """Increment inventory by getting current level and adding to it."""
        admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": admin_token,
            "Content-Type": "application/json",
        }

        client = self.get_client()
        
        try:
            # Get location ID
            location_query = "{ locations(first: 1) { edges { node { id } } } }"
            loc_res = await client.post(admin_url, json={"query": location_query}, headers=headers)
            loc_res.raise_for_status()
            loc_data = loc_res.json()
            
            if "errors" in loc_data or not loc_data.get("data", {}).get("locations", {}).get("edges"):
                print("Error fetching location")
                return

            location_id = loc_data["data"]["locations"]["edges"][0]["node"]["id"]
            
            # Get current inventory level
            inventory_query = """
            query getInventoryLevel($inventoryItemId: ID!, $locationId: ID!) {
              inventoryLevel(inventoryItemId: $inventoryItemId, locationId: $locationId) {
                available
              }
            }
            """
            
            inv_level_res = await client.post(
                admin_url,
                json={"query": inventory_query, "variables": {
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_id
                }},
                headers=headers
            )
            inv_level_res.raise_for_status()
            inv_level_data = inv_level_res.json()
            
            # Check for errors in the response
            if "errors" in inv_level_data:
                safe_print(f"[ERROR] GraphQL errors getting inventory level: {inv_level_data['errors']}")
                safe_print(f"[ERROR] Inventory Item ID might be invalid: {inventory_item_id}")
                return
            
            current_quantity = 0
            if "data" in inv_level_data and inv_level_data["data"].get("inventoryLevel"):
                current_quantity = inv_level_data["data"]["inventoryLevel"].get("available", 0)
                safe_print(f"[DEBUG] Current inventory level: {current_quantity}")
            else:
                safe_print(f"[WARNING] Could not get inventory level, response: {inv_level_data}")
                safe_print(f"[WARNING] Defaulting to current_quantity=0")
            
            # Calculate new total
            new_quantity = current_quantity + quantity_to_add
            
            safe_print(f"[DEBUG] Incrementing inventory: current={current_quantity}, adding={quantity_to_add}, new={new_quantity}")
            
            # Set new inventory level
            await self._update_inventory(admin_token, inventory_item_id, new_quantity)
                
        except Exception as e:
            print(f"Exception incrementing inventory: {str(e).encode('ascii', 'backslashreplace').decode()}")

    async def search_product_by_card(self, admin_token: str, card_number: str, card_name: str) -> Optional[dict]:
        """
        Search for a product by card number and name.
        Returns product info with variant ID if found, None otherwise.
        """
        admin_url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": admin_token,
            "Content-Type": "application/json",
        }

        # Search by title containing both card number and name
        search_query = f"{card_number} {card_name}"
        
        query = """
        query searchProducts($query: String!) {
          products(first: 10, query: $query) {
            edges {
              node {
                id
                title
                variants(first: 1) {
                  edges {
                    node {
                      id
                      price
                      inventoryQuantity
                      inventoryItem {
                        id
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"query": search_query}
        
        client = self.get_client()
        try:
            response = await client.post(
                admin_url,
                json={"query": query, "variables": variables},
                headers=headers
            )
            response.raise_for_status()
            res_data = response.json()
            
            if "errors" in res_data:
                print(f"Error searching products: {res_data['errors']}")
                return None
            
            products = res_data.get("data", {}).get("products", {}).get("edges", [])
            
            if not products:
                return None
            
            # Return the first matching product
            product_node = products[0]["node"]
            variant_node = product_node["variants"]["edges"][0]["node"]
            
            return {
                "product_id": product_node["id"],
                "variant_id": variant_node["id"],
                "inventory_item_id": variant_node["inventoryItem"]["id"],
                "title": product_node["title"],
                "price": float(variant_node.get("price", 0)),
                "current_quantity": variant_node.get("inventoryQuantity", 0)
            }
            
        except Exception as e:
            print(f"Exception searching for product: {str(e).encode('ascii', 'backslashreplace').decode()}")
            return None

    async def update_product(self, product_id: str, title: str = None, description: str = None, 
                            price: float = None, tags: list = None, vendor: str = None,
                            images_to_keep: list = None, images_to_add: list = None, collections: list = None) -> bool:
        """Update product information in Shopify.
        
        Args:
            images_to_keep: List of existing Shopify CDN URLs that should be kept
            images_to_add: List of new image URLs to add (uploaded files or external URLs)
        """
        token = os.getenv("SHOPIFY_ADMIN_TOKEN")
        if not token:
            print("[ERROR] No SHOPIFY_ADMIN_TOKEN found")
            return False
        
        shop_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
        admin_url = f"{shop_url}/admin/api/2024-01/graphql.json"
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        
        # Build input object with only provided fields
        input_fields = []
        if title is not None:
            input_fields.append(f'title: "{title}"')
        if description is not None:
            # Escape quotes in description
            escaped_desc = description.replace('"', '\\"').replace('\n', '\\n')
            input_fields.append(f'descriptionHtml: "{escaped_desc}"')
        if vendor is not None:
            input_fields.append(f'vendor: "{vendor}"')
        if tags is not None:
            tags_str = ', '.join([f'"{tag}"' for tag in tags])
            input_fields.append(f'tags: [{tags_str}]')
        
        # Note: Images and collections require separate mutations in Shopify
        # We'll handle them after the main product update
        
        input_str = ', '.join(input_fields)
        
        mutation = f"""
        mutation {{
          productUpdate(input: {{
            id: "{product_id}",
            {input_str}
          }}) {{
            product {{
              id
              title
            }}
            userErrors {{
              field
              message
            }}
          }}
        }}
        """
        
        client = self.get_client()
        try:
            response = await client.post(admin_url, json={"query": mutation}, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                print(f"[ERROR] GraphQL errors: {data['errors']}")
                return False
            
            user_errors = data.get("data", {}).get("productUpdate", {}).get("userErrors", [])
            if user_errors:
                print(f"[ERROR] User errors updating product: {user_errors}")
                return False
            
            # Update variant price if provided
            if price is not None:
                print(f"[DEBUG] Updating price to: {price}")
                # Get variant ID first
                product_data = await self.get_product(product_id)
                if product_data and product_data.get("variant_id"):
                    variant_id = product_data["variant_id"]
                    print(f"[DEBUG] Found variant ID: {variant_id}")
                    price_mutation = f"""
                    mutation {{
                      productVariantsBulkUpdate(productId: "{product_id}", variants: [{{
                        id: "{variant_id}",
                        price: "{price}"
                      }}]) {{
                        productVariants {{
                          id
                          price
                        }}
                        userErrors {{
                          field
                          message
                        }}
                      }}
                    }}
                    """
                    price_response = await client.post(admin_url, json={"query": price_mutation}, headers=headers)
                    price_response.raise_for_status()
                    price_data = price_response.json()
                    
                    print(f"[DEBUG] Price update response: {price_data}")
                    
                    price_errors = price_data.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
                    if price_errors:
                        print(f"[ERROR] User errors updating price: {price_errors}")
                        return False
                    else:
                        print(f"[SUCCESS] Price updated to {price}")
                else:
                    print(f"[ERROR] Could not get variant_id for price update")
            
            # Update images with smart deletion and addition
            if images_to_keep is not None or images_to_add is not None:
                try:
                    # Step 1: Get existing images from Shopify
                    product_query = f"""
                    query {{
                      product(id: "{product_id}") {{
                        media(first: 50) {{
                          edges {{
                            node {{
                              ... on MediaImage {{
                                id
                                image {{
                                  url
                                }}
                              }}
                            }}
                          }}
                        }}
                      }}
                    }}
                    """
                    
                    query_response = await client.post(admin_url, json={"query": product_query}, headers=headers)
                    query_response.raise_for_status()
                    query_data = query_response.json()
                    
                    existing_images = {}  # {url: id}
                    media_edges = query_data.get("data", {}).get("product", {}).get("media", {}).get("edges", [])
                    for edge in media_edges:
                        node = edge.get("node", {})
                        if node.get("id") and node.get("image", {}).get("url"):
                            # Extract base URL without query parameters for comparison
                            url = node["image"]["url"].split('?')[0]
                            existing_images[url] = node["id"]
                    
                    print(f"[DEBUG] Found {len(existing_images)} existing images in Shopify")
                    
                    # Step 2: Determine which images to delete
                    images_to_keep = images_to_keep or []
                    images_to_delete_ids = []
                    
                    for url, image_id in existing_images.items():
                        # Check if this URL is in the keep list (compare base URLs)
                        should_keep = False
                        for keep_url in images_to_keep:
                            keep_url_base = keep_url.split('?')[0]
                            if url == keep_url_base or keep_url_base in url:
                                should_keep = True
                                break
                        
                        if not should_keep:
                            images_to_delete_ids.append(image_id)
                    
                    print(f"[DEBUG] Images to KEEP: {len(images_to_keep)}")
                    print(f"[DEBUG] Images to DELETE: {len(images_to_delete_ids)}")
                    
                    # Step 3: Delete images that are not in the keep list
                    if images_to_delete_ids:
                        delete_mutation = f"""
                        mutation {{
                          productDeleteMedia(productId: "{product_id}", mediaIds: {str(images_to_delete_ids).replace("'", '"')}) {{
                            deletedMediaIds
                            deletedProductImageIds
                            userErrors {{
                              field
                              message
                            }}
                          }}
                        }}
                        """
                        
                        delete_response = await client.post(admin_url, json={"query": delete_mutation}, headers=headers)
                        delete_response.raise_for_status()
                        delete_data = delete_response.json()
                        
                        delete_errors = delete_data.get("data", {}).get("productDeleteMedia", {}).get("userErrors", [])
                        if delete_errors:
                            print(f"[WARNING] Errors deleting images: {delete_errors}")
                        else:
                            print(f"[SUCCESS] Deleted {len(images_to_delete_ids)} images")
                    
                    # Step 4: Add new images
                    images_to_add = images_to_add or []
                    if images_to_add:
                        images_input = []
                        for img_url in images_to_add:
                            images_input.append(f'{{ originalSource: "{img_url}", mediaContentType: IMAGE }}')
                        
                        images_str = ', '.join(images_input)
                        images_mutation = f"""
                        mutation {{
                          productCreateMedia(productId: "{product_id}", media: [{images_str}]) {{
                            media {{
                              ... on MediaImage {{
                                id
                                image {{
                                  url
                                }}
                              }}
                            }}
                            mediaUserErrors {{
                              field
                              message
                            }}
                          }}
                        }}
                        """
                        
                        print(f"[DEBUG] Adding {len(images_to_add)} new images")
                        
                        images_response = await client.post(admin_url, json={"query": images_mutation}, headers=headers)
                        images_response.raise_for_status()
                        images_data = images_response.json()
                        
                        print(f"[DEBUG] Images response: {images_data}")
                        
                        images_errors = images_data.get("data", {}).get("productCreateMedia", {}).get("mediaUserErrors", [])
                        if images_errors:
                            print(f"[WARNING] Errors adding new images: {images_errors}")
                        else:
                            print(f"[SUCCESS] Added {len(images_to_add)} new images")
                        
                except Exception as e:
                    print(f"[WARNING] Failed to update images: {str(e).encode('ascii', 'backslashreplace').decode()}")
            
            # Update collections if provided
            if collections is not None and len(collections) > 0:
                print(f"[DEBUG] Updating collections: {collections}")
                
                try:
                    # Step 1: Get collection IDs from titles
                    collection_ids = []
                    for collection_title in collections:
                        collection_query = f"""
                        query {{
                          collections(first: 10, query: "title:'{collection_title}'") {{
                            edges {{
                              node {{
                                id
                                title
                              }}
                            }}
                          }}
                        }}
                        """
                        
                        coll_response = await client.post(admin_url, json={"query": collection_query}, headers=headers)
                        coll_response.raise_for_status()
                        coll_data = coll_response.json()
                        
                        coll_edges = coll_data.get("data", {}).get("collections", {}).get("edges", [])
                        if coll_edges:
                            collection_id = coll_edges[0]["node"]["id"]
                            collection_ids.append(collection_id)
                            print(f"[DEBUG] Found collection '{collection_title}' with ID: {collection_id}")
                        else:
                            print(f"[WARNING] Collection '{collection_title}' not found in Shopify")
                    
                    # Step 2: Remove product from all collections first
                    # Get all current collections
                    current_colls_query = f"""
                    query {{
                      product(id: "{product_id}") {{
                        collections(first: 50) {{
                          edges {{
                            node {{
                              id
                            }}
                          }}
                        }}
                      }}
                    }}
                    """
                    
                    curr_coll_response = await client.post(admin_url, json={"query": current_colls_query}, headers=headers)
                    curr_coll_response.raise_for_status()
                    curr_coll_data = curr_coll_response.json()
                    
                    current_collection_ids = []
                    curr_edges = curr_coll_data.get("data", {}).get("product", {}).get("collections", {}).get("edges", [])
                    for edge in curr_edges:
                        current_collection_ids.append(edge["node"]["id"])
                    
                    # Remove from current collections
                    for coll_id in current_collection_ids:
                        remove_mutation = f"""
                        mutation {{
                          collectionRemoveProducts(id: "{coll_id}", productIds: ["{product_id}"]) {{
                            userErrors {{
                              field
                              message
                            }}
                          }}
                        }}
                        """
                        
                        await client.post(admin_url, json={"query": remove_mutation}, headers=headers)
                    
                    if current_collection_ids:
                        print(f"[DEBUG] Removed product from {len(current_collection_ids)} existing collections")
                    
                    # Step 3: Add product to new collections
                    for collection_id in collection_ids:
                        add_mutation = f"""
                        mutation {{
                          collectionAddProducts(id: "{collection_id}", productIds: ["{product_id}"]) {{
                            userErrors {{
                              field
                              message
                            }}
                          }}
                        }}
                        """
                        
                        add_response = await client.post(admin_url, json={"query": add_mutation}, headers=headers)
                        add_response.raise_for_status()
                        add_data = add_response.json()
                        
                        add_errors = add_data.get("data", {}).get("collectionAddProducts", {}).get("userErrors", [])
                        if add_errors:
                            print(f"[WARNING] Errors adding to collection: {add_errors}")
                        else:
                            print(f"[SUCCESS] Added product to collection {collection_id}")
                    
                    if collection_ids:
                        print(f"[SUCCESS] Collections updated successfully")
                        
                except Exception as e:
                    print(f"[WARNING] Failed to update collections: {str(e).encode('ascii', 'backslashreplace').decode()}")
            
            print(f"[SUCCESS] Product updated successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Exception updating product: {str(e).encode('ascii', 'backslashreplace').decode()}")
            return False
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete a product from Shopify.
        
        Args:
            product_id: The Shopify product ID (e.g., gid://shopify/Product/123)
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        token = os.getenv("SHOPIFY_ADMIN_TOKEN")
        if not token:
            print("[ERROR] No SHOPIFY_ADMIN_TOKEN found")
            return False
        
        shop_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
        admin_url = f"{shop_url}/admin/api/2024-01/graphql.json"
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        
        mutation = f"""
        mutation {{
          productDelete(input: {{id: "{product_id}"}}) {{
            deletedProductId
            userErrors {{
              field
              message
            }}
          }}
        }}
        """
        
        client = self.get_client()
        try:
            print(f"[DEBUG] Deleting product: {product_id}")
            response = await client.post(admin_url, json={"query": mutation}, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                print(f"[ERROR] GraphQL errors: {data['errors']}")
                return False
            
            user_errors = data.get("data", {}).get("productDelete", {}).get("userErrors", [])
            if user_errors:
                print(f"[ERROR] User errors deleting product: {user_errors}")
                return False
            
            deleted_id = data.get("data", {}).get("productDelete", {}).get("deletedProductId")
            if deleted_id:
                print(f"[SUCCESS] Product deleted: {deleted_id}")
                return True
            else:
                print("[ERROR] Product deletion did not return deletedProductId")
                return False
                
        except Exception as e:
            print(f"[ERROR] Exception deleting product: {str(e).encode('ascii', 'backslashreplace').decode()}")
            return False


def get_shopify_client() -> ShopifyClient:
    return ShopifyClient()
