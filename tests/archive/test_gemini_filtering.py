"""
Test Gemini filtering with real card: Pikachu sA #001/024
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.appraisal import get_market_value_jpy

async def test_pikachu_sa():
    """Test appraisal for Pikachu sA #001/024"""
    
    print("=" * 80)
    print("Testing Gemini Filtering with: ピカチュウ (Pikachu) - Pikachu sA #001/024")
    print("=" * 80)
    
    # Card details from Shopify
    card_name = "Pikachu Pikachu sA"  # Cleaned name (as extracted by admin.py)
    rarity = "Common"
    set_name = ""  # No set in tags
    card_number = "#001/024"
    variants = ["Japanese"]
    
    print(f"\nCard Details:")
    print(f"  Name: {card_name}")
    print(f"  Rarity: {rarity}")
    print(f"  Set: {set_name or 'N/A'}")
    print(f"  Number: {card_number}")
    print(f"  Variants: {variants}")
    
    print(f"\n{'='*80}")
    print("Starting Appraisal...")
    print(f"{'='*80}\n")
    
    # Call the appraisal service
    result = await get_market_value_jpy(
        card_name=card_name,
        rarity=rarity,
        set_name=set_name,
        card_number=card_number,
        variants=variants
    )
    
    print(f"\n{'='*80}")
    print("Appraisal Result:")
    print(f"{'='*80}")
    
    if 'error' in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"Market Value (USD): ${result['market_usd']}")
        print(f"Market Value (JPY): Y{result['market_jpy']:,}")
        print(f"Exchange Rate: {result['exchange_rate']}")
        print(f"Rate Date: {result['rate_date']}")
        print(f"Confidence: {result['confidence']}")
    
    print(f"\n{'='*80}")
    print("Test Complete!")
    print(f"{'='*80}\n")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_pikachu_sa())

