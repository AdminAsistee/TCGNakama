"""
Test Pikachu s10a #014/071 appraisal
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.appraisal import get_market_value_jpy

async def test_pikachu_s10a():
    print("=" * 80)
    print("Testing: Pikachu s10a #014/071")
    print("=" * 80)
    
    # Test twice to see if there's a difference
    for attempt in [1, 2]:
        print(f"\n--- Attempt {attempt} ---")
        result = await get_market_value_jpy(
            card_name="Pikachu s10a",
            rarity="Common",
            set_name="s10a",
            card_number="#014/071",
            variants=["Japanese"]
        )
        
        print(f"\nResult:")
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        else:
            print(f"Market Value (USD): ${result['market_usd']}")
            print(f"Market Value (JPY): ¥{result['market_jpy']:,}")
            print(f"Confidence: {result.get('confidence', 'N/A')}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_pikachu_s10a())
