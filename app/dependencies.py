import os
import httpx
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)

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
            "price": float(variant.get("price", {}).get("amount", 0)),
            "image": node.get("featuredImage", {}).get("url") if node.get("featuredImage") else "https://images.pokemontcg.io/bg.jpg",
            "badge": rarity.upper(),
            "badge_color": "bg-primary" if rarity == "Common" else "bg-green-500",
            "card_number": card_number,
            "totalInventory": total_inventory,
            "createdAt": node.get("createdAt"),
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
                "productType": product_data.get("product_type", "Trading Card"),
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

            # 2. Update the default variant price and sku (since we couldn't do it in step 1)
            variant_mutation = """
            mutation productVariantUpdate($input: ProductVariantInput!) {
              productVariantUpdate(input: $input) {
                productVariant {
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
            variant_vars = {
                "input": {
                    "id": variant_id,
                    "price": str(product_data["price"]),
                    "sku": product_data.get("sku", "")
                }
            }
            
            var_resp = await client.post(
                admin_url,
                json={"query": variant_mutation, "variables": variant_vars},
                headers=headers
            )
            var_data = var_resp.json()
            if "errors" in var_data:
                print(f"Warning: Failed to update variant price: {var_data['errors']}")
            elif var_data.get("data", {}).get("productVariantUpdate", {}).get("userErrors"):
                print(f"Warning: Shopify User Error updating variant: {var_data['data']['productVariantUpdate']['userErrors']}")

            # 3. Update inventory if quantity > 0
            quantity = product_data.get("quantity", 1)
            if quantity > 0:
                await self._update_inventory(admin_token, inventory_item_id, quantity)

            return product
        except Exception as e:
            print(f"Error creating product: {str(e).encode('ascii', 'backslashreplace').decode()}")
            raise

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
        
        loc_res = await client.post(admin_url, json={"query": location_query}, headers=headers)
        loc_data = loc_res.json()
        if not loc_data.get("data", {}).get("locations", {}).get("edges"):
            print("No locations found, skipping inventory update")
            return

        location_id = loc_data["data"]["locations"]["edges"][0]["node"]["id"]

        # Now set the level
        inventory_mutation = """
        mutation inventorySet($input: InventorySetQuantitiesInput!) {
          inventorySetQuantities(input: $input) {
            inventoryLevels {
              id
              available
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        inventory_vars = {
            "input": {
                "name": "available",
                "reason": "correction",
                "quantities": [
                    {
                        "inventoryItemId": inventory_item_id,
                        "locationId": location_id,
                        "quantity": quantity
                    }
                ]
            }
        }

        # Since 2024-01 uses inventorySetQuantities
        await client.post(
            admin_url,
            json={"query": inventory_mutation, "variables": inventory_vars},
            headers=headers
        )

def get_shopify_client() -> ShopifyClient:
    return ShopifyClient()
