"""
Debug - Check what the 5 Luffy OP13-001 results are
"""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re

card_name = "Monkey D Luffy"
card_number = "OP13-001"

search_query = f"{card_name} OP13 {card_number}"
encoded_query = quote_plus(search_query)
url = f"https://www.pricecharting.com/search-products?q={encoded_query}&type=prices"

print(f"Search URL: {url}\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

with httpx.Client(timeout=10.0, follow_redirects=True) as client:
    response = client.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract results
    rows = soup.find_all('tr')
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
        match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
        if match:
            price = float(match.group(1).replace(',', ''))
            if price > 0:
                results.append({"name": card_title, "price": price})
    
    print(f"Total results: {len(results)}\n")
    
    # Filter by OP13-001
    filtered = [r for r in results if 'OP13-001' in r['name']]
    
    print(f"Results containing 'OP13-001': {len(filtered)}\n")
    print("All OP13-001 results (sorted by price):")
    print("=" * 100)
    
    filtered.sort(key=lambda x: x['price'])
    
    for i, result in enumerate(filtered, 1):
        print(f"{i}. ${result['price']:<8} - {result['name']}")
