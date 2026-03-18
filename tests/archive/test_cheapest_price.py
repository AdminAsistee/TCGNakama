# -*- coding: utf-8 -*-
"""Test cheapest price extraction"""

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

async def test_cheapest_price():
    print("="*60)
    print("TESTING CHEAPEST PRICE EXTRACTION")
    print("="*60)
    
    # Test with Pikachu sA
    result = await appraisal.get_market_value_jpy(
        card_name="Pikachu sA",
        rarity="Common",
        set_name="",
        card_number="#001/024",
        variants=["Japanese"]
    )
    
    print("\nRESULT:")
    print(f"Market USD: ${result.get('market_usd')}")
    print(f"Market JPY: ¥{result.get('market_jpy'):,}")
    print("="*60)

asyncio.run(test_cheapest_price())
