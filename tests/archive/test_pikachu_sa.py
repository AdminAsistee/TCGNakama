# -*- coding: utf-8 -*-
"""Test specific card: Pikachu sA #001/024"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, r'c:\Users\amrca\Documents\antigravity\tcgnakama')

from app.services.appraisal import _try_pokemontcg_api, _try_pricecharting_scrape, _try_ebay_scrape

# Test card: Pikachu sA #001/024
card_name = "Pikachu sA"  # "sA" is a special grade/variant
set_name = "Unknown"  # No set specified
rarity = "Common"
card_number = "#001/024"
is_japanese = True

print("="*60)
print("TESTING: Pikachu sA #001/024")
print("="*60)
print(f"Card: {card_name}")
print(f"Set: {set_name}")
print(f"Number: {card_number}")
print(f"Japanese: {is_japanese}")
print("="*60)

# Test Source 1: PokemonTCG.io
print("\nSource 1: PokemonTCG.io API")
print("-" * 60)
try:
    price = _try_pokemontcg_api(card_name, set_name, rarity, card_number, is_japanese)
    if price:
        print(f"SUCCESS: ${price}")
    else:
        print("FAILED: No price found")
except Exception as e:
    print(f"ERROR: {e}")

# Test Source 2: PriceCharting (with progressive fallback)
print("\n" + "="*60)
print("\nSource 2: PriceCharting (Progressive Fallback)")
print("-" * 60)
try:
    price = _try_pricecharting_scrape(card_name, set_name, card_number, is_japanese)
    if price:
        print(f"SUCCESS: ${price}")
    else:
        print("FAILED: No price found")
except Exception as e:
    print(f"ERROR: {e}")

# Test Source 3: eBay
print("\n" + "="*60)
print("\nSource 3: eBay Sold Listings")
print("-" * 60)
try:
    price = _try_ebay_scrape(card_name, set_name, card_number, is_japanese)
    if price:
        print(f"SUCCESS: ${price}")
    else:
        print("FAILED: No price found")
except Exception as e:
    print(f"ERROR: {e}")

# Also test without "sA" to see if it makes a difference
print("\n" + "="*60)
print("\nCOMPARISON: Without 'sA' variant")
print("="*60)
print("\nPriceCharting: Just 'Pikachu' (no sA)")
print("-" * 60)
try:
    price = _try_pricecharting_scrape("Pikachu", set_name, card_number, is_japanese)
    if price:
        print(f"SUCCESS: ${price}")
    else:
        print("FAILED: No price found")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "="*60)
print("Test complete!")
