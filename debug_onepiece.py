"""
Debug One Piece card search on PriceCharting
"""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# Card details
card_name = "Monkey D Luffy"  # Cleaned name
card_number = "#OP13-001"
set_name = "OP13"

# Build search query
query_parts = [card_name, card_number]
search_query = " ".join(query_parts)
encoded_query = quote_plus(search_query)
url = f"https://www.pricecharting.com/search-products?q={encoded_query}&type=prices"

print(f"Search Query: {search_query}")
print(f"URL: {url}\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

with httpx.Client(timeout=10.0, follow_redirects=True) as client:
    response = client.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        exit(1)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find table rows
    rows = soup.find_all('tr')
    print(f"Found {len(rows)} rows\n")
    
    # Extract results
    results = []
    for row in rows:
        name_elem = row.find('td', class_='title')
        if not name_elem:
            continue
            
        card_title = name_elem.get_text(strip=True)
        
        price_elem = row.find('td', class_='used_price')
        if not price_elem:
            continue
            
        price_text = price_elem.get_text(strip=True)
        
        results.append({"name": card_title, "price": price_text})
    
    print(f"Results found: {len(results)}\n")
    
    if results:
        print("Cards found:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['name']} - {result['price']}")
    else:
        print("No results found!")
        print("\nTrying alternative search...")
        
        # Try without card number
        alt_query = card_name
        alt_encoded = quote_plus(alt_query)
        alt_url = f"https://www.pricecharting.com/search-products?q={alt_encoded}&type=prices"
        
        print(f"Alternative URL: {alt_url}\n")
        
        response2 = client.get(alt_url, headers=headers)
        soup2 = BeautifulSoup(response2.text, 'html.parser')
        rows2 = soup2.find_all('tr')
        
        print(f"Found {len(rows2)} rows with alternative search")
        
        for row in rows2[:5]:  # Show first 5
            name_elem = row.find('td', class_='title')
            if name_elem:
                print(f"  - {name_elem.get_text(strip=True)}")
