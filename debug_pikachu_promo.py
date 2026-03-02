"""
Debug Pikachu 120/SV-P search - check ALL rows
"""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# Card details
card_name = "Pikachu"
card_number = "120/SV-P"

# Build search query
search_query = f"{card_name} {card_number}"
encoded_query = quote_plus(search_query)
url = f"https://www.pricecharting.com/search-products?q={encoded_query}&type=prices"

print(f"Search Query: {search_query}")
print(f"URL: {url}\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

with httpx.Client(timeout=10.0, follow_redirects=True) as client:
    response = client.get(url, headers=headers)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr')
    
    print(f"Total rows: {len(rows)}\n")
    print("First 10 rows with title elements:")
    print("=" * 80)
    
    count = 0
    for row in rows:
        name_elem = row.find('td', class_='title')
        if name_elem:
            card_title = name_elem.get_text(strip=True)
            
            # Check for price
            price_elem = row.find('td', class_='used_price')
            price_text = price_elem.get_text(strip=True) if price_elem else "NO PRICE"
            
            print(f"{count+1}. {card_title}")
            print(f"   Price: {price_text}")
            print()
            
            count += 1
            if count >= 10:
                break
    
    if count == 0:
        print("No rows with 'title' class found!")
        print("\nChecking for any <td> elements in first row:")
        if rows:
            first_row = rows[0]
            tds = first_row.find_all('td')
            for i, td in enumerate(tds):
                print(f"  TD {i}: class='{td.get('class')}' text='{td.get_text(strip=True)[:50]}'")
