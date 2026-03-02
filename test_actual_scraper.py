# -*- coding: utf-8 -*-
"""Test with actual scraper function"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, r'c:\Users\amrca\Documents\antigravity\tcgnakama')

from app.services.appraisal import _try_pricecharting_scrape

# Test the actual function
card_name = "Pikachu sA"
set_name = ""  # No set name in the URL
card_number = "#001/024"
is_japanese = False  # Not using Japanese keyword anymore

print("="*60)
print("TESTING ACTUAL SCRAPER FUNCTION")
print("="*60)
print(f"Card: {card_name}")
print(f"Set: {set_name}")
print(f"Number: {card_number}")
print(f"Japanese: {is_japanese}")
print("="*60)

try:
    price = _try_pricecharting_scrape(card_name, set_name, card_number, is_japanese)
    if price:
        print(f"\nSUCCESS: ${price}")
    else:
        print(f"\nFAILED: No price found")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Test complete!")
