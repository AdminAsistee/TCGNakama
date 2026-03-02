"""
Test One Piece card appraisal with fixed search
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.appraisal import get_market_value_jpy

async def test_onepiece():
    """Test appraisal for Monkey D. Luffy OP13-001"""
    
    print("=" * 80)
    print("Testing: Monkey D. Luffy OP13 #OP13-001")
    print("=" * 80)
    
    card_name = "Monkey D Luffy"
    rarity = "Common"
    set_name = "OP13"
    card_number = "#OP13-001"
    variants = ["Japanese"]
    
    print(f"\nCard Details:")
    print(f"  Name: {card_name}")
    print(f"  Set: {set_name}")
    print(f"  Number: {card_number}")
    
    print(f"\n{'='*80}")
    print("Starting Appraisal...")
    print(f"{'='*80}\n")
    
    result = await get_market_value_jpy(
        card_name=card_name,
        rarity=rarity,
        set_name=set_name,
        card_number=card_number,
        variants=variants
    )
    
    print(f"\n{'='*80}")
    print("Result:")
    print(f"{'='*80}")
    
    if 'error' in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"Market Value (USD): ${result['market_usd']}")
        print(f"Market Value (JPY): Y{result['market_jpy']:,}")
        print(f"Expected: ~Y18,370 ($119.50 * 153.71)")
    
    print(f"\n{'='*80}\n")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_onepiece())
