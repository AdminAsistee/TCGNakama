"""
Debug - Check what PriceCharting has for Pikachu 018/051
"""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# Try different search queries
queries = [
    "Pikachu 018/051",
    "Pikachu 18/51",
    "Pikachu SML",
    "Pikachu SM-L",
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

for query in queries:
    print(f"\n{'='*80}")
    print(f"Testing query: '{query}'")
    print(f"{'='*80}")
    
    encoded_query = quote_plus(query)
    url = f"https://www.pricecharting.com/search-products?q={encoded_query}&type=prices"
    
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find results with prices
        rows = soup.find_all('tr')
        results = []
        
        for row in rows:
            name_elem = row.find('td', class_='title')
            if not name_elem:
                continue
                
            card_title = name_elem.get_text(strip=True)
            
            price_elem = row.find('td', class_='used_price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                results.append({"name": card_title, "price": price_text})
        
        print(f"Found {len(results)} results with prices")
        
        if results:
            print("\nFirst 5 results:")
            for i, result in enumerate(results[:5], 1):
                print(f"{i}. {result['name']} - {result['price']}")
        else:
            print("No results with prices found")
            
            # Check for suggestion links
            game_links = soup.find_all('a', href=lambda x: x and '/game/' in x)
            if game_links:
                print(f"\nFound {len(game_links)} suggestion links:")
                for i, link in enumerate(game_links[:3], 1):
                    print(f"{i}. {link.get_text(strip=True)} -> {link.get('href')}")
