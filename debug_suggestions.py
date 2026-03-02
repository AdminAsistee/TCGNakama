"""
Debug - Check what links are on the Pikachu search page
"""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

card_name = "Pikachu"
card_number = "#120/SV-P"
clean_number = card_number.replace('#', '')

search_query = f"{card_name} {clean_number}"
encoded_query = quote_plus(search_query)
url = f"https://www.pricecharting.com/search-products?q={encoded_query}&type=prices"

print(f"Search URL: {url}\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

with httpx.Client(timeout=10.0, follow_redirects=True) as client:
    response = client.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all links with /game/ in them
    game_links = soup.find_all('a', href=lambda x: x and '/game/' in x)
    
    print(f"Found {len(game_links)} links with '/game/' in href\n")
    print("First 10 game links:")
    print("=" * 80)
    
    search_number = card_number.replace('#', '').replace('/', '').lower()
    print(f"Looking for: '{search_number}' in href\n")
    
    for i, link in enumerate(game_links[:20]):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Check if this link matches
        href_clean = href.lower().replace('-', '')
        matches = search_number in href_clean
        
        print(f"{i+1}. {'✓' if matches else ' '} {text[:60]}")
        print(f"   {href}")
        if matches:
            print(f"   *** MATCH! ***")
        print()
