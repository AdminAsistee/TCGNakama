"""
Test Luffy OP13-001 appraisal to debug pricing
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.appraisal import get_market_value_jpy

async def test_luffy():
    print("=" * 80)
    print("Testing: Monkey D. Luffy OP13-001")
    print("=" * 80)
    
    result = await get_market_value_jpy(
        card_name="Monkey D Luffy",
        rarity="Common",
        set_name="OP13",
        card_number="#OP13-001",
        variants=["Japanese"]
    )
    
    print(f"\nResult:")
    if 'error' in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"Market Value (USD): ${result['market_usd']}")
        print(f"Market Value (JPY): Y{result['market_jpy']:,}")
        print(f"\nExpected regular version: ~$0.51 (Y78)")
        print(f"Actual result: ${result['market_usd']} (Y{result['market_jpy']})")
        
        if result['market_usd'] > 1.0:
            print(f"\n⚠️ WARNING: Price seems too high for regular version!")
            print(f"This might be a special variant being selected.")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_luffy())
