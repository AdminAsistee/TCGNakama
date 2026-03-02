"""
Debug script to inspect PriceCharting HTML structure
"""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# Build search query
search_name = "Pikachu sA"
card_number = "#001/024"
query_parts = [search_name, card_number]
search_query = " ".join(query_parts)
encoded_query = quote_plus(search_query)
url = f"https://www.pricecharting.com/search-products?q={encoded_query}&type=prices"

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
    
    # Save HTML to file for inspection
    with open('pricecharting_debug.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    
    print("HTML saved to pricecharting_debug.html\n")
    
    # Try to find table rows
    print("Looking for table rows...")
    rows = soup.find_all('tr')
    print(f"Found {len(rows)} rows\n")
    
    # Try different selectors for card names
    print("Trying different selectors for card names:")
    print("-" * 80)
    
    # Try 1: <a class='title'>
    titles_1 = soup.find_all('a', class_='title')
    print(f"1. <a class='title'>: {len(titles_1)} found")
    if titles_1:
        for i, title in enumerate(titles_1[:3]):
            print(f"   - {title.get_text(strip=True)}")
    
    # Try 2: <a> tags in general
    all_links = soup.find_all('a')
    print(f"\n2. All <a> tags: {len(all_links)} found")
    
    # Try 3: <td> with class containing 'title' or 'name'
    title_tds = soup.find_all('td', class_=lambda x: x and ('title' in x.lower() or 'name' in x.lower()))
    print(f"\n3. <td> with 'title' or 'name' class: {len(title_tds)} found")
    if title_tds:
        for i, td in enumerate(title_tds[:3]):
            print(f"   - {td.get_text(strip=True)}")
    
    # Try 4: Look at first few rows in detail
    print(f"\n4. First 5 table rows in detail:")
    print("-" * 80)
    for i, row in enumerate(rows[:5]):
        print(f"\nRow {i}:")
        cells = row.find_all(['td', 'th'])
        for j, cell in enumerate(cells):
            classes = cell.get('class', [])
            text = cell.get_text(strip=True)[:50]
            print(f"  Cell {j} (class={classes}): {text}")
    
    # Try 5: Find price elements
    print(f"\n5. Looking for price elements:")
    print("-" * 80)
    price_elements = soup.find_all('td', class_='price')
    print(f"Found {len(price_elements)} price elements")
    if price_elements:
        for i, price_elem in enumerate(price_elements[:3]):
            print(f"   - {price_elem.get_text(strip=True)}")

print("\nDebug complete!")
