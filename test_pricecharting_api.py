"""
Test script to verify PriceCharting API key is working
"""
import asyncio
import httpx
from urllib.parse import quote_plus

async def test_pricecharting_api():
    api_key = "40d8d65da33130a111830698dac61dfe04099357"
    
    # Test with the Pikachu card
    search_query = "Pikachu sA 001/024"
    url = f"https://www.pricecharting.com/api/products?t={api_key}&q={quote_plus(search_query)}"
    
    print("=" * 80)
    print("Testing PriceCharting API")
    print("=" * 80)
    print(f"API Key: {api_key[:20]}...")
    print(f"Search Query: {search_query}")
    print(f"URL: {url}")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Length: {len(response.text)} bytes")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n[SUCCESS] API KEY IS WORKING!")
                print(f"\nProducts Found: {len(data.get('products', []))}")
                
                if data.get('products'):
                    print("\nFirst 3 Results:")
                    for i, product in enumerate(data['products'][:3], 1):
                        name = product.get('product-name', 'Unknown')
                        loose = product.get('loose-price', 'N/A')
                        cib = product.get('cib-price', 'N/A')
                        new = product.get('new-price', 'N/A')
                        
                        print(f"\n{i}. {name}")
                        print(f"   Loose: ${loose}")
                        print(f"   Complete: ${cib}")
                        print(f"   New: ${new}")
                else:
                    print("\n[WARNING] No products found for this search")
            
            elif response.status_code == 401:
                print("\n[ERROR] API KEY IS INVALID!")
                print("Error: Unauthorized - Check your API key")
            
            elif response.status_code == 403:
                print("\n[ERROR] API KEY IS FORBIDDEN!")
                print("Error: Access denied - API key may be expired or blocked")
            
            else:
                print(f"\n[ERROR] UNEXPECTED STATUS CODE: {response.status_code}")
                print(f"Response: {response.text[:500]}")
    
    except Exception as e:
        print(f"\n[ERROR] {e}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_pricecharting_api())
