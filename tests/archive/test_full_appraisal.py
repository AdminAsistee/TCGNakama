# -*- coding: utf-8 -*-
"""Test the full appraisal flow"""

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

async def test_full_appraisal():
    print("="*60)
    print("TESTING FULL APPRAISAL FLOW")
    print("="*60)
    
    # Test card
    card_name = "Pikachu sA"
    rarity = "Common"
    set_name = ""
    card_number = "#001/024"
    variants = []  # No Japanese variant
    
    print(f"Card: {card_name}")
    print(f"Set: {set_name}")
    print(f"Number: {card_number}")
    print(f"Rarity: {rarity}")
    print(f"Variants: {variants}")
    print("="*60)
    
    # Call the full appraisal function
    result = await appraisal.get_market_value_jpy(
        card_name=card_name,
        rarity=rarity,
        set_name=set_name,
        card_number=card_number,
        variants=variants
    )
    
    print("\nRESULT:")
    print(result)
    print("\n" + "="*60)

# Run the async function
asyncio.run(test_full_appraisal())
