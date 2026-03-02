#!/usr/bin/env python3
"""Fix the card number matching logic to use all variations."""

import re
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Read the file
with open('app/services/appraisal.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the matching logic
old_code = """                for item in filtered_prices:  # Search in filtered_prices, not valid_prices
                    # Normalize product name the same way
                    product_normalized = re.sub(r'[#\\-/\\s]', '', item['name']).upper()
                    
                    # Check if the normalized search number appears in the product name
                    if search_normalized in product_normalized:
                        number_matches.append(item)
                        safe_print(f"[PRICECHARTING_API]   ✓ Matched: '{item['name']}'")"""

new_code = """                for item in filtered_prices:  # Search in filtered_prices, not valid_prices
                    product_name_upper = item['name'].upper()
                    
                    # Check if any variation appears in the product name
                    for variation in variations:
                        if variation in product_name_upper:
                            number_matches.append(item)
                            safe_print(f"[PRICECHARTING_API]   ✓ Number match ('{variation}'): '{item['name']}'")
                            break  # Don't check other variations for this item"""

# Replace
if old_code in content:
    content = content.replace(old_code, new_code)
    print("SUCCESS: Found and replaced matching logic")
else:
    print("ERROR: Could not find the old code pattern")
    print("\nSearching for similar patterns...")
    # Try to find the line
    if "for item in filtered_prices:" in content:
        print("  - Found 'for item in filtered_prices:'")
    if "search_normalized in product_normalized" in content:
        print("  - Found 'search_normalized in product_normalized'")

# Write back
with open('app/services/appraisal.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! File updated.")
