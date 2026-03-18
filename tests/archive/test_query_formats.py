"""
Test different query formats to find the best match
"""
import asyncio
import httpx
from urllib.parse import quote_plus

async def test_query(api_key, query, description):
    url = f"https://www.pricecharting.com/api/products?t={api_key}&q={quote_plus(query)}"
    
    print(f"\n{'='*80}")
    print(f"Test: {description}")
    print(f"Query: '{query}'")
    print(f"{'='*80}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                print(f"Found {len(products)} products\n")
                
                for i, product in enumerate(products[:3], 1):
                    name = product.get('product-name', 'Unknown')
                    loose = product.get('loose-price', 'N/A')
                    print(f"{i}. {name} - ${loose}")
            else:
                print(f"Error: Status {response.status_code}")
    
    except Exception as e:
        print(f"Error: {e}")

async def main():
    api_key = "40d8d65da33130a111830698dac61dfe04099357"
    
    # Test different query formats
    queries = [
        ("Pikachu sA 001/024", "Current format (with slash)"),
        ("Pikachu sA 001", "Without total count"),
        ("Pikachu sA #001", "With # symbol"),
        ("pokemon pikachu sA 001", "With 'pokemon' prefix"),
        ("pikachu japanese starter set sa", "Descriptive search"),
        ("pikachu v starter set", "V Starter Set"),
        ("pikachu thunder starter set", "Thunder Starter Set"),
    ]
    
    for query, desc in queries:
        await test_query(api_key, query, desc)
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
