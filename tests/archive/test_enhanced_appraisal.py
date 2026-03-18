# -*- coding: utf-8 -*-
"""Test enhanced appraisal with card number and Japanese detection"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, r'c:\Users\amrca\Documents\antigravity\tcgnakama')

from app.services.appraisal import _try_pokemontcg_api, _try_pricecharting_scrape, _try_ebay_scrape

# Test card with Japanese name and card number
card_name = "Pikachu"
set_name = "VMAX Starter Set"
rarity = "Common"
card_number = "#001/024"
is_japanese = True  # Detected from Japanese characters

print("="*60)
print("ENHANCED APPRAISAL TEST")
print("="*60)
print(f"Card: {card_name}")
print(f"Set: {set_name}")
print(f"Number: {card_number}")
print(f"Japanese: {is_japanese}")
print("="*60)

# Test Source 1: PokemonTCG.io with enhanced search
print("\nSource 1: PokemonTCG.io API (with set + number)")
print("-" * 60)
try:
    price = _try_pokemontcg_api(card_name, set_name, rarity, card_number, is_japanese)
    if price:
        print(f"SUCCESS: ${price}")
    else:
        print("FAILED: No price found")
except Exception as e:
    print(f"ERROR: {e}")

# Test Source 2: PriceCharting with enhanced search
print("\n" + "="*60)
print("\nSource 2: PriceCharting (with set + number + Japanese)")
print("-" * 60)
try:
    price = _try_pricecharting_scrape(card_name, set_name, card_number, is_japanese)
    if price:
        print(f"SUCCESS: ${price}")
    else:
        print("FAILED: No price found")
except Exception as e:
    print(f"ERROR: {e}")

# Test Source 3: eBay with enhanced search
print("\n" + "="*60)
print("\nSource 3: eBay (with set + number + Japanese)")
print("-" * 60)
try:
    price = _try_ebay_scrape(card_name, set_name, card_number, is_japanese)
    if price:
        print(f"SUCCESS: ${price}")
    else:
        print("FAILED: No price found")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "="*60)
print("\nCOMPARISON: Without enhancements")
print("="*60)

# Compare with old search (no number, no Japanese)
print("\nPriceCharting (OLD - no number/Japanese)")
print("-" * 60)
try:
    price = _try_pricecharting_scrape(card_name, set_name, "", False)
    if price:
        print(f"OLD RESULT: ${price}")
    else:
        print("FAILED: No price found")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "="*60)
print("Test complete!")
