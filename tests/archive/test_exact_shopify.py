# -*- coding: utf-8 -*-
"""Test appraisal with exact Shopify product values"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, r'c:\Users\amrca\Documents\antigravity\tcgnakama')

import asyncio
from app.services import appraisal
import re

async def test_exact_shopify_values():
    print("="*60)
    print("TESTING WITH EXACT SHOPIFY VALUES")
    print("="*60)
    
    # Exact values from Shopify product
    card_title = "ピカチュウ (Pikachu) - Pikachu sA #001/024"
    set_tag = "sA"
    card_number_tag = "001/024"
    
    print(f"Original Title: {card_title}")
    print(f"Set Tag: {set_tag}")
    print(f"Number Tag: {card_number_tag}")
    print("="*60)
    
    # Simulate the extraction logic from admin.py
    search_name = card_title
    
    # Remove Japanese characters and parentheses
    search_name = re.sub(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\(\)]', '', search_name)
    
    # Remove card number pattern
    search_name = re.sub(r'#?\d+/\d+', '', search_name)
    
    # Remove extra dashes and whitespace
    search_name = re.sub(r'\s*-\s*', ' ', search_name).strip()
    search_name = ' '.join(search_name.split())
    
    # Add # to card number
    card_number = f"#{card_number_tag}"
    
    # Ignore short set names
    set_name = '' if len(set_tag) <= 3 else set_tag
    
    print(f"Extracted search_name: '{search_name}'")
    print(f"Extracted set_name: '{set_name}'")
    print(f"Extracted card_number: '{card_number}'")
    print("="*60)
    
    # Call appraisal
    result = await appraisal.get_market_value_jpy(
        card_name=search_name,
        rarity="Common",
        set_name=set_name,
        card_number=card_number,
        variants=["Japanese"]
    )
    
    print("\nRESULT:")
    print(result)
    print("\n" + "="*60)

asyncio.run(test_exact_shopify_values())
