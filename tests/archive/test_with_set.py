# -*- coding: utf-8 -*-
"""Test Pikachu sA with proper set name"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, r'c:\Users\amrca\Documents\antigravity\tcgnakama')

from app.services.appraisal import _try_pokemontcg_api, _try_pricecharting_scrape, _try_ebay_scrape

# Test with different set names to see what works
test_cases = [
    ("Pikachu sA", "VMAX Starter Set", "#001/024", True),
    ("Pikachu sA", "Starter Set", "#001/024", True),
    ("Pikachu sA", "Pokemon", "#001/024", True),
    ("Pikachu", "VMAX Starter Set", "#001/024", True),
]

for card_name, set_name, card_number, is_japanese in test_cases:
    print("="*60)
    print(f"Testing: {card_name} | Set: {set_name} | Number: {card_number}")
    print("="*60)
    
    # Test PriceCharting
    print("\nPriceCharting:")
    try:
        price = _try_pricecharting_scrape(card_name, set_name, card_number, is_japanese)
        if price:
            print(f"  SUCCESS: ${price}")
        else:
            print(f"  FAILED: No price found")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Test eBay
    print("\neBay:")
    try:
        price = _try_ebay_scrape(card_name, set_name, card_number, is_japanese)
        if price:
            print(f"  SUCCESS: ${price}")
        else:
            print(f"  FAILED: No price found")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    print()

print("="*60)
print("Test complete!")
