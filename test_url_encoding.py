# -*- coding: utf-8 -*-
"""Test URL encoding"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Test different query formats
test_queries = [
    ("Pikachu sA", "", "#001/024"),
    ("Pikachu sA", "VMAX Starter Set", "#001/024"),
]

for card_name, set_name, card_number in test_queries:
    search_name = card_name.split('(')[0].strip()
    query_parts = [search_name]
    
    if set_name and set_name != "Unknown":
        query_parts.append(set_name)
    
    query_parts.append(card_number)
    
    search_query = " ".join(query_parts).replace(' ', '+')
    url = f"https://www.pricecharting.com/search-products?q={search_query}&type=prices"
    
    print("="*60)
    print(f"Card: {card_name}")
    print(f"Set: {set_name}")
    print(f"Number: {card_number}")
    print(f"\nQuery parts: {query_parts}")
    print(f"Search query: {search_query}")
    print(f"\nFinal URL:")
    print(url)
    print()

print("="*60)
print("\nWorking URL from user:")
print("https://www.pricecharting.com/search-products?q=Pikachu+sA+%23001%2F024&type=prices")
