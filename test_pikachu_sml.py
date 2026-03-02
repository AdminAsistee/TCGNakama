"""
Test Pikachu SML #018/051 appraisal
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.appraisal import get_market_value_jpy

async def test_pikachu_sml():
    print("=" * 80)
    print("Testing: Pikachu SML #018/051")
    print("=" * 80)
    
    result = await get_market_value_jpy(
        card_name="Pikachu SML",
        rarity="Common",
        set_name="SML",
        card_number="#018/051",
        variants=["Japanese"]
    )
    
    print(f"\nResult:")
    if 'error' in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"Market Value (USD): ${result['market_usd']}")
        print(f"Market Value (JPY): Y{result['market_jpy']}")
        print(f"Confidence: {result.get('confidence', 'N/A')}")
        print(f"Status: {result.get('status', 'N/A')}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_pikachu_sml())
